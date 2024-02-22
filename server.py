# server.py

from flask import jsonify
import random
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from functools import wraps

import psycopg2, os
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
from contextlib import contextmanager

from flask import Flask, render_template, request, url_for, flash, redirect, session

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')
app.secret_key = env.get("FLASK_SECRET")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

def setup():
    global pool
    DATABASE_URL = os.environ['DATABASE_URL']
    pool = ThreadedConnectionPool(1, 100, dsn=DATABASE_URL, sslmode='require')


@contextmanager
def get_db_connection():
    try:
        connection = pool.getconn()
        yield connection
    finally:
        pool.putconn(connection)


@contextmanager
def get_db_cursor(commit=True):
    with get_db_connection() as connection:
      cursor = connection.cursor(cursor_factory=DictCursor)
      try:
          yield cursor
          if commit:
              connection.commit()
      finally:
          cursor.close()

@app.before_request
def initialize():
    setup()


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )
    
# saves the session for the user and bypasses the need for them to login again when they return
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    #  this is when you finish a login/registration, do more work here
    #  if new user add to database, is login, add
    session["user"] = token
    print(token)
    # check the data, the precence of the token represents a user we just dont jknow what kind
    # 
    return redirect("/")   


# clears the user session in your app and redirects to the Auth0 logout endpoint 
@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("launch", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

@app.route("/")
@app.route("/launch")
def launch():
    return render_template("launch.html")

@app.route("/firstLogin", methods=["GET"])
def firstLogin():
    return render_template("first-login.html")

@app.route("/home")
def home():
    top_5_books = top5()
    print("top 5 in home")
    print(top_5_books)
    # rand_genre = random.randint(0, 10)
    # print(rand_genre)
    # match rand_genre:
    #     case 0:
    #         genre = "Action"
    #     case 1: 
    #         genre = "Adventure"
    #     case 2:
    #         genre = "Fantasy"
    #     case 3: 
    #         genre = "Romance"
    #     case 4:
    #         genre = "Mystery"
    #     case 5: 
    #         genre = "Crime"
    #     case 6:
    #         genre = "Historical"
    #     case 7: 
    #         genre = "SciFi"
    #     case 8:
    #         genre = "Horror"
    #     case 9: 
    #         genre = "Poetry"
    #     case 10:
    #         genre = "Comedy"
    # print(genre)
    genre="Fantasy"
    top_5_genre = top5genre(genre)
    return render_template("home.html", top_5_books=top_5_books, top_5_genre=top_5_genre, genre=genre)

@app.route("/story/<int:storyId>/<int:chapterNum>/")
def getStory(storyId, chapterNum):
    print("getting chapter")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT content FROM chapters WHERE book_id = %s AND chapter_id = %s", (storyId, chapterNum))
        chapter_content = cursor.fetchone()

        cursor.execute("SELECT title FROM books WHERE book_id = %s", (storyId,))
        book_title = cursor.fetchone()

        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (storyId,))
        num_chapters = cursor.fetchone()

    return render_template("story.html", storyId = storyId, chapterNum = chapterNum, chapter_content =  chapter_content, book_title = book_title, num_chapters = num_chapters)

def get_book_details(book_id):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book_details = cursor.fetchone()
    return book_details

def get_chapter_details(book_id, chapter_id):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s AND chapter_id = %s", (book_id, chapter_id))
        chapter_details = cursor.fetchone()
    return chapter_details


@app.route("/user/<string:username>")
def getUser(username):
    # if logged in user is the same as the user request, then set true
    # session=session.get('user')
    # print("session: ")
    # print(session)
    # if 'user' in session:
    #     logged_in = True
    # else:
    #     logged_in = False
    logged_in = True
    print("getting user")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_info = cursor.fetchone()
    user_id = user_info[0]
    pfp_url = user_info[3]
    bio = user_info[4]
    published_books =  (user_info[7].split(", "))
    library_books = (user_info[8].split(", "))

    published_books_info = []
    library_books_info = []

    for book_id in published_books:
        book_info = get_book_details(book_id)
        published_books_info.append(book_info)

    for book_id in library_books:
        book_info = get_book_details(book_id)
        library_books_info.append(book_info)

    return render_template("user.html", user_id = user_id, logged_in=logged_in, username = username, pfp_url = pfp_url, bio = bio, published_books = published_books_info, library_books = library_books_info)



# FOR ONCE ACCOUNTS ARE ESTABLISHED
# @app.route("/user/<string:username>")
# def getUser(username):
#     print("getting user profile")
#     return render_template("profile.html")



## STORY EDITING PAGES - OVERVIEW AND WRITING PAGE


@app.route("/myworks/<int:book_id>", methods=["GET"])    #(STORY OVERVIEW PAGE)
# this is a page where the user can customize their book details. I.E., title, image, summary, genre, tags, etc. They can also create a new chapter, edit a chapter, etc. If the book already exists, the info will be prefilled from database. If not, the form is just empty.  
def storyoverview(book_id): 
    book_details = get_book_details(book_id)    
    print(book_details)
    return render_template("storydetail.html", book_details = book_details)

@app.route("/myworks/<int:book_id>", methods=["POST"])
def updateOverview(book_id):
    book_title = request.form.get('book_title')
    genre = request.form.get('genre')
    summary = request.form.get('summary')
    return storyoverview(book_id)

@app.route("/myworks/<int:book_id>/<int:chapter_id>", methods=["GET"])   #(EDITING CHAPTER PAGE)
def editChapter(book_id, chapter_id):
    # this is similar to the story page Shriya made, but it can edit the text and save to publish the chapter. If the chapter is new, it'll already be in the database but with empty content. SO either way, just display the content. 
    print("getting chapter")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT content FROM chapters WHERE book_id = %s AND chapter_id = %s", (book_id, chapter_id))
        chapter_content = cursor.fetchone()

        cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
        book_title = cursor.fetchone()

        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (book_id,))
        num_chapters = cursor.fetchone()
    
    return render_template("saveChapter.html", book_id = book_id, chapterNum = chapter_id, chapter_content =  chapter_content, book_title = book_title, num_chapters = num_chapters)
    # CODE OUTLINE
    # get current chapter content, chapter number, book title, (maybe) book_id from database
    # render an HTML page, returning this info
    # the HTML page should a be simple for with one text box, where the user can edit the 
    # content of the chapter. 
    # there will be a save page where users can save their edits.
    # the save page calls the api "/myworks/api/<book_id>/<chapter_id>/updatechapter"
    



@app.route("/myworks/<int:storyId>/delete", methods=["DELETE"])
def deleteStory():
    print("deletes story, deletes entry in DB")
    # return render_template("deleteStory.html")


# APIs for story overview and writing page
@app.route("/myworks/api/newbook/<int:user_id>", methods=["POST"])

# this API is called whe user clicks "NEW STORY"
# story is initialied with empty string for everything we don't have data for
# defualt image URL IS: https://thumbs.dreamstime.com/b/paper-texture-smooth-pastel-pink-color-perfect-background-uniform-pure-minimal-photo-trendy-149575202.jpg
# story title is intialized as "Untitled Story"
# chpater 1 should be made, with empty content


@app.route("/myworks/api/<int:book_id>/updatebook", methods=["PUT"])
# updates the details of the book. Called when the user clicks "save" on the /myworks/<book_id> page. 


@app.route("/myworks/api/<int:book_id>/createchapter", methods=["POST"])
def createchapter(book_id):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            return jsonify({"message": "Book not found"}), 404
        num_chapters = book[0]
        print(num_chapters)

        cursor.execute("INSERT INTO chapters (chapter_id, book_id, content) VALUES (%s, %s, %s)", (num_chapters + 1, book_id, ''))

        if cursor.rowcount > 0:
            return jsonify({"message": "Chapter added successfully"}), 200
        else:
            return jsonify({"message": "Failed to add chapter"}), 500
        
@app.route("/myworks/api/<book_id>/<chapter_id>/updatechapter", methods=["POST"])
def updatechapter(book_id, chapter_id):
    updated_content = request.form.get('chapter_content')
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM chapters WHERE book_id = %s AND chapter_id = %s", (book_id, chapter_id))
        existing_chapter = cursor.fetchone()
        if existing_chapter:
            cursor.execute("UPDATE chapters SET content = %s WHERE book_id = %s AND chapter_id = %s", (updated_content, book_id, chapter_id))
        else:
            cursor.execute("INSERT INTO chapters (chapter_id, book_id, content) VALUES (%s, %s, %s)", (chapter_id, book_id, updated_content))
            cursor.execute("UPDATE books SET num_chapters = num_chapters + 1 WHERE book_id = %s", (book_id,))
    return storyoverview(book_id)
    

@app.route("/myworks/api/<int:book_id>/delete", methods=["DELETE"])
# book is deleted from database. 
# called when "delete" is clicked on the story detail page. 

@app.route("/myworks/api/<book_id>/<chapter_id>/delete", methods=["DELETE"])
# this can be done last, we don't need it. 
# book chapter is deleted from database. 
# called when "delete" chpater is clicked from the story detail page. 


## HOME PAGE APIs
@app.route("/api/top5", methods=["GET"])
def top5():
    "SELECT * FROM books ORDER BY num_likes DESC LIMIT 5"
    with get_db_cursor() as cursor:
        cursor.execute( "SELECT * FROM books ORDER BY num_likes DESC LIMIT 5")
        top_5 = cursor.fetchall()
    return top_5

@app.route("/api/top5/<string:genre>", methods=["GET"])
def top5genre(genre):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM books WHERE LOWER(genre) = LOWER(%s) ORDER BY num_likes DESC LIMIT 5", (genre,))
        top_5 = cursor.fetchall()
    return top_5


# Need to add more later !!!
@app.route("/search/", methods=["GET"])
@app.route("/search", methods=["GET"])
def search():
    print("search")
    print(request.query_string)
    search = request.args.get('query')
    print(search)

    return render_template("search.html", search=search)


# USER RELATED APIs
@app.route("/api/currentuser")
def currentuser():
    # find current user with session ID
    return 0

    

@app.route("/api/userlibrary")
def userlibrary():
    current_user_email = currentuser()['email'] #assuming current users returns a JSON
    with get_db_cursor() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (current_user_email,))
        current_user_id = cursor.fetchone()
        cursor.execute("SELECT * FROM books WHERE user_id = %s", (current_user_id,))
        library = cursor.fetchall()


    return jsonify(library)