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

pool = None

def setup():
    global pool
    DATABASE_URL = os.getenv("DATABASE_URL")
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


def authenticate_user(requested_user):

    # first, see if any user is logged in
    # if not, return access denied
    try: 
        current_user_session = session["user"]
    except:
        return False
    
    
    # then, check if its the correct user
    current_user_email = current_user_session.get("userinfo").get("name")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE email = %s", (current_user_email,))
        current_username = cursor.fetchone()

    if (requested_user != current_username[0]):
        return False
    
    return True

def authenticate_book(requested_book):
    # first, see if any user is logged in
    # if not, return access denied
    try: 
        current_user_session = session["user"]
    except:
        return False

    # then, check if the user has access to their book
    current_user_email = current_user_session.get("userinfo").get("name")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (current_user_email,))
        current_user_id = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM books WHERE book_id = %s AND user_id = %s", (requested_book, current_user_id))
        selected_book = cursor.fetchall()

    print(current_user_id)
    print(requested_book)
    print(selected_book)
    if (len(selected_book) == 1):
        return True
    
    return False

def get_current_user():
    try:
        user_email = session["user"].get("userinfo").get("name")
        with get_db_cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE email = %s", (user_email,))
            current_username = cursor.fetchone()[0]
            return current_username
    except:
        return "guest"


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
    user_email = token.get("userinfo").get("name")

    with get_db_cursor() as cursor:
        cursor.execute("SELECT email, username FROM users WHERE email = %s", (user_email,))
        user_data = cursor.fetchall()

    if len(user_data) == 1:
        user_name = user_data[0][1]
        return redirect(f"/home/{user_name}")
    else:
        # add user to database
        return render_template("first-login.html", email=user_email)



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

@app.route("/home/<string:current_user>")
def home(current_user):
    
    logged_in =  authenticate_user(current_user)

    print(logged_in)

    top_5_books = top5()
    rand_genre = random.randint(0, 7)
    genre = ""
    match rand_genre:
        case 0:
            genre = "Action"
        case 1: 
            genre = "Action"
        case 2:
            genre = "Romance"
        case 3: 
            genre = "Contemporary"
        case 4:
            genre = "Horror"
        case 5: 
            genre = "Comedy"
        case 6:
            genre = "SciFi"
    top_5_genre = top5genre(genre)
    if logged_in:
        print(current_user)
        user_library = userlibrary(current_user)
    else:
        user_library = []
    return render_template("home.html", top_5_books=top_5_books, top_5_genre=top_5_genre, user_library=user_library, genre=genre, current_user=current_user, logged_in=logged_in)

@app.route("/story/<int:storyId>/<int:chapterNum>/")
def getStory(storyId, chapterNum):
    print("getting chapter")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT content FROM chapters WHERE book_id = %s AND chapter_id = %s", (storyId, chapterNum))
        chapter_content = cursor.fetchone()
        print(chapter_content)

        cursor.execute("SELECT title FROM books WHERE book_id = %s", (storyId,))
        book_title = cursor.fetchone()

        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (storyId,))
        num_chapters = cursor.fetchone()

        cursor.execute("SELECT user_id FROM books WHERE book_id = %s", (storyId,))
        author_id = cursor.fetchone()

        cursor.execute("SELECT username FROM users WHERE user_id = %s", (author_id))
        author_name = cursor.fetchone()

    current_user = get_current_user()
    return render_template("story.html", author_id = author_id, author_name = author_name, storyId = storyId, chapterNum = chapterNum, chapter_content =  chapter_content, book_title = book_title, num_chapters = num_chapters, current_user=current_user)


@app.route("/story/<int:book_id>", methods=["GET"])    #(STORY OVERVIEW PAGE - USER (NOT AUTHOR) ACESSS )
# this is a page where the user can customize their book details. I.E., title, image, summary, genre, tags, etc. They can also create a new chapter, edit a chapter, etc. If the book already exists, the info will be prefilled from database. If not, the form is just empty.  
def storydetail(book_id): 
    current_user = get_current_user()
    print(current_user)
    logged_in = authenticate_user(current_user)
    print(logged_in)
    book_details = get_book_details(book_id) 
    if logged_in: 
        with get_db_cursor() as cursor:
            cursor.execute("SELECT library_books FROM users WHERE username = %s", (current_user,))
            library_books = cursor.fetchone()[0]
            library_books = library_books.split(", ")
            is_in_library = str(book_id) in library_books
            
            author_id = book_details[1]
            print("author_id", author_id)
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (author_id,))
            author_name = cursor.fetchone()
            print("book details", book_details)

            print("author", author_name)
    else:
        library_books = []
        is_in_library = False
    current_user=get_current_user()
    return render_template("storydetail.html", book_details = book_details, book_id = book_id, logged_in = logged_in, is_in_library = is_in_library, current_user=current_user, author_name=author_name)

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
    ## AUTHENTICATE USER
    if not authenticate_user(username):
        logged_in = False
    else: logged_in = True
    print("getting user")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_info = cursor.fetchone()
    user_id = user_info[0]
    bio = user_info[2]
    published_books =  user_info[4].split(", ")
    library_books = user_info[5].split(", ")

    published_books_info = []
    library_books_info = []

    if published_books[0] != '':
        for book_id in published_books:
            book_info = get_book_details(book_id)
            published_books_info.append(book_info)

    if library_books[0] != '':
        for book_id in library_books:
            book_info = get_book_details(book_id)
            library_books_info.append(book_info)

    current_user = get_current_user()
    return render_template("user.html", user_id = user_id, logged_in=logged_in, username = username, bio = bio, published_books = published_books_info, library_books = library_books_info, current_user=current_user)



## STORY EDITING PAGES - OVERVIEW AND WRITING PAGE


@app.route("/myworks/<int:book_id>", methods=["GET"])    #(STORY OVERVIEW PAGE - AUTHOR ACCESS)
# this is a page where the user can customize their book details. I.E., title, image, summary, genre, tags, etc. They can also create a new chapter, edit a chapter, etc. If the book already exists, the info will be prefilled from database. If not, the form is just empty.  
def storyoverview(book_id): 
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
    book_details = get_book_details(book_id)    
    current_user = get_current_user()
    return render_template("storylaunch.html", book_details = book_details, current_user=current_user)

@app.route("/myworks/api/updatebook/<int:book_id>", methods=["POST"])
def updateOverview(book_id):
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
    book_title = request.form.get('book_title')
    genre = request.form.get('genre')
    tags = request.form.get('tags')
    summary = request.form.get('summary')
    image = request.form.get('book_image')
    with get_db_cursor() as cursor:
        cursor.execute("UPDATE books SET title = %s, genre = %s, tags = %s, summary = %s, picture_url = %s WHERE book_id = %s", (book_title, genre, tags, summary, image, book_id))
    return redirect(url_for('storyoverview', book_id=book_id))

@app.route("/myworks/<int:book_id>/<int:chapter_id>", methods=["GET"])   #(EDITING CHAPTER PAGE)
def editChapter(book_id, chapter_id):
    # this is similar to the story page Shriya made, but it can edit the text and save to publish the chapter. If the chapter is new, it'll already be in the database but with empty content. SO either way, just display the content. 
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT content FROM chapters WHERE book_id = %s AND chapter_id = %s", (book_id, chapter_id))
        chapter_content = cursor.fetchone()

        cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
        book_title = cursor.fetchone()

        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (book_id,))
        num_chapters = cursor.fetchone()
    
    current_user = get_current_user()
    return render_template("saveChapter.html", book_id = book_id, chapterNum = chapter_id, chapter_content =  chapter_content, book_title = book_title, num_chapters = num_chapters, current_user=current_user)
    


@app.route("/myworks/api/<int:book_id>/delete", methods=["GET"])
def deleteStory(book_id):
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
    current_user = get_current_user()
    with get_db_cursor() as cursor: 
        cursor.execute("DELETE FROM books where book_id = %s", (book_id,))
        cursor.execute("DELETE FROM chapters where book_id = %s", (book_id,))
        cursor.execute("SELECT published_books FROM users WHERE username = %s", (current_user,))
        published_library = cursor.fetchone()[0]
        published_library_books = published_library.split(", ") if published_library else []
        if str(book_id) in published_library_books:
            published_library_books.remove(str(book_id))
            print("Deleting published book from library")
        
        updated_list = ", ".join(published_library_books)
        cursor.execute("UPDATE users SET published_books = %s WHERE username = %s", (updated_list, current_user))
        
        cursor.execute("SELECT username FROM users WHERE library_books LIKE %s", ('%' + str(book_id) + '%',))
        users_with_book = cursor.fetchall()
        for user in users_with_book:
            username = user[0]
            cursor.execute("SELECT library_books FROM users WHERE username = %s", (username,))
            library = cursor.fetchone()[0]
            library_books = library.split(", ") if library else []
            if str(book_id) in library_books:
                library_books.remove(str(book_id))
                updated_library = ", ".join(map(str, library_books))
                cursor.execute("UPDATE users SET library_books = %s WHERE username = %s", (updated_library, username))

    return redirect(url_for('getUser', username=current_user))


# APIs for story overview and writing page
@app.route("/myworks/api/newbook/<int:user_id>", methods=["POST"])
def create_new_book(user_id): 
    with get_db_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        current_username = cursor.fetchone()[0]
    print(current_username)
    if not authenticate_user(current_username):
        return render_template("accessdenied.html")
    default_title = 'Untitled Story'
    default_image_url = 'https://thumbs.dreamstime.com/b/paper-texture-smooth-pastel-pink-color-perfect-background-uniform-pure-minimal-photo-trendy-149575202.jpg'
    with get_db_cursor() as cursor:
        cursor.execute("INSERT INTO books (user_id, title, picture_url, num_chapters, genre, tags, summary) VALUES (%s, %s, %s, %s, %s, %s, %s)", (user_id, default_title, default_image_url,1, '', '{}', ''))
        cursor.execute("SELECT LASTVAL()")
        new_book_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO chapters (chapter_id, book_id, content) VALUES (%s, %s, %s)", (1, new_book_id, ''))
        
        cursor.execute("SELECT published_books FROM users WHERE user_id = %s", (user_id,))
        published_books = cursor.fetchone()[0]
        if published_books != '':
            published_books += f", {new_book_id}"
        else:
            published_books = str(new_book_id)

        cursor.execute("UPDATE users SET published_books = %s WHERE user_id = %s", (published_books, user_id))
    
    return redirect(url_for('storyoverview', book_id=new_book_id))

@app.route("/story/<book_id>/save" , methods=["POST"])
def save_book(book_id):
    current_user = get_current_user()
    with get_db_cursor() as cursor:
        cursor.execute("SELECT num_saved FROM books WHERE book_id = %s", (book_id,))
        num_saved = cursor.fetchone()[0]

        cursor.execute("SELECT library_books FROM users WHERE username = %s", (current_user,))
        library_books = cursor.fetchone()[0]
        library_books_list = library_books.split(",") if library_books else []
        if book_id in library_books_list:
            library_books_list.remove(book_id)
            num_saved -= 1
            print("Removing book from library")
        else:
            print("adding book to library")
            library_books_list.append(book_id)
            num_saved += 1
        updated_library_books = ", ".join(library_books_list)
        cursor.execute("UPDATE users SET library_books = %s WHERE username = %s", (updated_library_books, current_user))
        cursor.execute("UPDATE books SET num_saved = %s WHERE book_id = %s", (num_saved, book_id))
    return storydetail(book_id = book_id)

        
@app.route("/myworks/api/<book_id>/<chapter_id>/updatechapter", methods=["POST"])
def updatechapter(book_id, chapter_id):
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
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
    

# @app.route("/myworks/api/<int:book_id>/delete", methods=["DELETE"])
# book is deleted from database. 
# called when "delete" is clicked on the story detail page. 

@app.route("/myworks/api/<book_id>/<chapter_id>/delete", methods=["GET"])
# this can be done last, we don't need it. 
# book chapter is deleted from database. 
# called when "delete" chpater is clicked from the story detail page. 
def deleteChapter(book_id, chapter_id):
    print("deleting chapter")
    with get_db_cursor() as cursor: 
        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (book_id,))
        num_chapters = cursor.fetchone()[0]
        cursor.execute("DELETE FROM chapters WHERE chapter_id = %s AND book_id = %s", (chapter_id, book_id))
        num_chapters -= 1
        cursor.execute("UPDATE books SET num_chapters = %s WHERE book_id = %s", (num_chapters, book_id))
    return storyoverview(book_id = book_id)


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
    logged_in = (get_current_user() != "guest")
    print("search")
    print(request.query_string)
    search = request.args.get('query')
    print(search)

    current_user = get_current_user()
    return render_template("search.html", search=search, current_user=current_user, logged_in=logged_in)

@app.route("/search/filter/", methods=["GET"])
@app.route("/search/filter", methods=["GET"])
def filter_search():
    print("filtering search")
    print(request)



# USER RELATED APIs
@app.route("/api/adduser", methods=["POST"])
def adduser():
    username = request.form.get('stacked-name')
    bio = request.form.get('stacked-bio')
    email = request.form.get('email')

    # Print or do something with the data
    print(f"Username: {username}, Bio: {bio}, Emai: {email}")

    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO users 
            (username, bio, email, published_books, library_books) 
            VALUES (%s, %s, %s, %s, %s)
        """, (username, bio, email, '', ''))

    return redirect(f"/home/{username}")
    

@app.route("/api/userlibrary/<string:current_user>")
def userlibrary(current_user):
    # current_user_email = currentuser()['email'] #assuming current users returns a JSON
    if not authenticate_user(current_user):
        return render_template("accessdenied.html")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT library_books FROM users WHERE username = %s", (current_user,))
        library_books = cursor.fetchone()[0]

    library_books = library_books.split(", ")

    library_books_info = []

    if library_books[0] != '':
        for book_id in library_books:
            book_info = get_book_details(book_id)
            library_books_info.append(book_info)


    return library_books_info

