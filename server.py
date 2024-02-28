# server.py

# Import statements
from flask import Flask, render_template, request, url_for, flash, redirect, session
from flask import jsonify
from authlib.integrations.flask_client import OAuth
from functools import wraps
from os import environ as env
from urllib.parse import quote_plus, urlencode
import psycopg2
import random
import os
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
from contextlib import contextmanager

# Initialize Flask app
app = Flask(__name__, static_url_path='/static')
app.secret_key = env.get("FLASK_SECRET")

# Initialize OAuth for authentication
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

# Authentication Functions
def authenticate_user(requested_user):
    try: 
        current_user_session = session["user"]
    except:
        return False
    current_user_email = current_user_session.get("userinfo").get("name")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE email = %s", (current_user_email,))
        current_username = cursor.fetchone()
    return (requested_user == current_username[0])

def authenticate_book(requested_book):
    try: 
        current_user_session = session["user"]
    except:
        return False
    current_user_email = current_user_session.get("userinfo").get("name")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (current_user_email,))
        current_user_id = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM books WHERE book_id = %s AND user_id = %s", (requested_book, current_user_id))
        selected_book = cursor.fetchall()

    return (len(selected_book) == 1)

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

    top_5_books = top5()
    rand_genre = random.randint(0, 6)
    genre = ""
    match rand_genre:
        case 0:
            genre = "Fantasy"
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
            genre = "Sci-Fi"
    top_5_genre = top5genre(genre)
    if logged_in:
        user_library = userlibrary(current_user)
    else:
        user_library = []
    return render_template("home.html", top_5_books=top_5_books, top_5_genre=top_5_genre, user_library=user_library, genre=genre, current_user=current_user, logged_in=logged_in)

## Home Page Helper Functions
def top5():
    with get_db_cursor() as cursor:
        cursor.execute( "SELECT * FROM books ORDER BY num_saved DESC LIMIT 5")
        top_5 = cursor.fetchall()
    return top_5

def top5genre(genre):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM books WHERE LOWER(genre) = LOWER(%s) ORDER BY num_saved DESC LIMIT 5", (genre,))
        top_5 = cursor.fetchall()
    return top_5

def userlibrary(current_user):
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

@app.route("/story/<int:book_id>/<int:chapter_num>/")
def getstory(book_id, chapter_num):
    current_user = get_current_user()
    logged_in = authenticate_user(current_user)
    with get_db_cursor() as cursor:
        cursor.execute("SELECT content FROM chapters WHERE book_id = %s AND chapter_id = %s", (book_id, chapter_num))
        chapter_content = cursor.fetchone()

        cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
        book_title = cursor.fetchone()

        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (book_id,))
        num_chapters = cursor.fetchone()

        cursor.execute("SELECT user_id FROM books WHERE book_id = %s", (book_id,))
        author_id = cursor.fetchone()

        cursor.execute("SELECT username FROM users WHERE user_id = %s", (author_id))
        author_name = cursor.fetchone()

    return render_template("story.html", author_id = author_id, author_name = author_name, book_id = book_id, chapter_num = chapter_num, chapter_content =  chapter_content, book_title = book_title, num_chapters = num_chapters, current_user=current_user, logged_in=logged_in)

@app.route("/story/<int:book_id>", methods=["GET"])
def storydetail(book_id): 
    current_user = get_current_user()
    logged_in = authenticate_user(current_user)
    book_details = get_book_details(book_id) 
    if logged_in: 
        with get_db_cursor() as cursor:
            cursor.execute("SELECT library_books FROM users WHERE username = %s", (current_user,))
            library_books = cursor.fetchone()[0]
            library_books = library_books.split(", ")
            is_in_library = str(book_id) in library_books
            author_id = book_details[1]
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (author_id,))
            author_name = cursor.fetchone()
    else:
        library_books = []
        is_in_library = False
        author_name = ""
    current_user=get_current_user()
    return render_template("storydetail.html", book_details = book_details, book_id = book_id, logged_in = logged_in, is_in_library = is_in_library, current_user=current_user, author_name=author_name)

# story helper functions
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
def get_user_profile(username):
    logged_in = authenticate_user(username)
    current_user = get_current_user()
    nav_logged_in = (current_user != "guest")
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

    return render_template("user.html", user_id = user_id, logged_in=logged_in, username = username, bio = bio, published_books = published_books_info, library_books = library_books_info, current_user=current_user, nav_logged_in=nav_logged_in)

@app.route("/myworks/<int:book_id>", methods=["GET"]) # Author Editing
def storyoverview(book_id): 
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
    book_details = get_book_details(book_id)    
    current_user = get_current_user()
    return render_template("storylaunch.html", book_details = book_details, current_user=current_user, logged_in=True)

@app.route("/myworks/api/updatebook/<int:book_id>", methods=["POST"])
def updateOverview(book_id):
    if not (authenticate_book(book_id)):
        return render_template("accessdenied.html")
    book_title = request.form.get('book_title')
    genre = request.form.get('genre')
    tags = request.form.get('tags')
    summary = request.form.get('summary')
    image = request.form.get('book_image')
    current_user = get_current_user()
    logged_in = authenticate_user(current_user)
    if logged_in:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE books SET title = %s, genre = %s, tags = %s, summary = %s, picture_url = %s WHERE book_id = %s", (book_title, genre, tags, summary, image, book_id))
    return redirect(f"/myworks/{book_id}")

@app.route("/myworks/<int:book_id>/<int:chapter_id>", methods=["GET"])
def editChapter(book_id, chapter_id):
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
    return render_template("saveChapter.html", book_id = book_id, chapterNum = chapter_id, chapter_content =  chapter_content, book_title = book_title, num_chapters = num_chapters, current_user=current_user, logged_in=True)

# APIs for story overview and writing page
@app.route("/myworks/api/<int:book_id>/delete", methods=["GET", "DELETE"])
def deletestory(book_id):
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

    return redirect(url_for('get_user_profile', username=current_user))

@app.route("/myworks/api/newbook/<int:user_id>", methods=["POST"])
def create_new_book(user_id): 
    with get_db_cursor() as cursor:
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        current_username = cursor.fetchone()[0]
    if not authenticate_user(current_username):
        return render_template("accessdenied.html")
    default_title = 'Untitled Story'
    default_image_url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR-_sWn0slVMyhl_bQJ3vGYbFK0c3o5_8zoWA&usqp=CAU'
    with get_db_cursor() as cursor:
        cursor.execute("INSERT INTO books (user_id, title, picture_url, num_chapters, genre, tags, summary) VALUES (%s, %s, %s, %s, %s, %s, %s)", (user_id, default_title, default_image_url,1, '', '', ''))
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
        else:
            library_books_list.append(book_id)
            num_saved += 1
        updated_library_books = ", ".join(library_books_list)
        cursor.execute("UPDATE users SET library_books = %s WHERE username = %s", (updated_library_books, current_user))
        cursor.execute("UPDATE books SET num_saved = %s WHERE book_id = %s", (num_saved, book_id))
    return redirect(f"/story/{book_id}")

@app.route("/myworks/api/<book_id>/<chapter_id>/updatechapter", methods=["POST"])
def update_chapter(book_id, chapter_id):
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
    return redirect(f"/myworks/{book_id}")


@app.route("/myworks/api/<book_id>/<chapter_id>/delete", methods=["GET"])
def deletechapter(book_id, chapter_id):
    with get_db_cursor() as cursor: 
        cursor.execute("SELECT num_chapters FROM books WHERE book_id = %s", (book_id,))
        num_chapters = cursor.fetchone()[0]
        cursor.execute("DELETE FROM chapters WHERE chapter_id = %s AND book_id = %s", (chapter_id, book_id))
        num_chapters -= 1
        cursor.execute("UPDATE books SET num_chapters = %s WHERE book_id = %s", (num_chapters, book_id))
    return redirect(f"/myworks/{book_id}")

@app.route("/search/", methods=["GET"])
@app.route("/search", methods=["GET"])
def search():
    logged_in = (get_current_user() != "guest")
    search_query = request.args.get('query')

    book_query_results = get_book_id_results(search_query)
    book_results = []

    with get_db_cursor() as cursor:
        if book_query_results != [] and book_query_results[0] != '':
            for book_id in book_query_results:
                book_info = get_book_details(book_id)
                cursor.execute("SELECT username FROM users WHERE user_id = %s", (book_info[1],))
                username = cursor.fetchone()[0]
                book_info.append(username)
                book_results.append(book_info)
    
    user_query_results = get_user_id_results(search_query)
    user_results = []

    if user_query_results != [] and user_query_results[0] != '':
        for user_id in user_query_results:
            user_info = get_user_details(user_id)
            user_results.append(user_info)
        

    current_user = get_current_user()
    return render_template("search.html", search=search_query, current_user=current_user, logged_in=logged_in, book_results=book_results, user_results=user_results)

# SEARCH HELPER FUNCTIONS
def get_book_id_results(search_query):
    results = []

    # Search in chapters, book descriptions, book titles, and user books in a single query
    with get_db_cursor() as cursor:
        combined_query = """
            SELECT DISTINCT book_id FROM (
                SELECT book_id FROM chapters
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                UNION
                SELECT book_id FROM books
                WHERE to_tsvector('english', summary) @@ plainto_tsquery('english', %s)
                UNION
                SELECT book_id FROM books
                WHERE to_tsvector('english', title) @@ plainto_tsquery('english', %s)
                UNION
                SELECT book_id FROM books
                WHERE user_id IN (SELECT user_id FROM users WHERE to_tsvector('english', username) @@ plainto_tsquery('english', %s))
            ) AS combined_results
        """
        cursor.execute(combined_query, (search_query, search_query, search_query, search_query))
        results.extend([row[0] for row in cursor.fetchall()])

    # Remove duplicates and sort by frequency
    counts = {x: results.count(x) for x in results}
    unique_sorted_results = sorted(counts.keys(), key=lambda x: counts[x], reverse=True)

    return unique_sorted_results

def get_user_id_results(search_query):

    results = []

    # Search in users database and return user_ids
    with get_db_cursor() as cursor:
        user_query = """
            SELECT user_id FROM users
            WHERE to_tsvector('english', username) @@ plainto_tsquery('english', %s)
        """
        cursor.execute(user_query, (search_query,))
        results.extend([row[0] for row in cursor.fetchall()])

    # gets rid of duplicate results, but sorts by most common result
    counts = {x: results.count(x) for x in results}
    unique_sorted_results = sorted(counts.keys(), key=lambda x: counts[x], reverse=True)
    return unique_sorted_results


def get_user_details(user_id):
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_details = cursor.fetchone()
    return user_details


@app.route("/search/filter/", methods=["GET"])
@app.route("/search/filter", methods=["GET"])
def filter_search():
    logged_in = (get_current_user() != "guest")

    search_query = request.args.get("search_query")
    chapterRange = request.args.get("chapterRange")
    savedRange = request.args.get("range")
    tags = request.args.get("tags").split(", ")

    default_genres = ["Action", "Horror", "Fantasy", "Romance", "Comedy", "Sci-Fi", "Contemporary"]
    chosen_genres = ["none"]
    for genre in default_genres:
        if request.args.get(genre) == "On":
            chosen_genres.append(genre)

    current_books = get_book_id_results(search_query)

    # get a list of books where the book_id is in the book_results list
    # AND the genre of the book is in the chosen_genres list
    with get_db_cursor() as cursor:
        # query for everything but tags 
        query = """
            SELECT b.book_id
            FROM books b
            JOIN chapters c ON b.book_id = c.book_id
            WHERE (b.num_chapters <= %s)
            AND (b.genre IN %s)
            AND (b.num_saved < %s)
            AND b.book_id IN %s
        """
        cursor.execute(query, (chapterRange, tuple(chosen_genres), savedRange, tuple(current_books)))
        filtered_book_results = [row[0] for row in cursor.fetchall()]

        # query for tags
        query = """
            SELECT book_id
            FROM books
            WHERE (
                SELECT COUNT(*)
                FROM unnest(string_to_array(tags, ', ')) AS book_tag
                WHERE book_tag = ANY(%s)
            ) > 0
            AND genre IN %s
        """

        cursor.execute(query, (tags, tuple(chosen_genres)))
        filtered_book_results = [row[0] for row in cursor.fetchall()]

    book_results = []

    with get_db_cursor() as cursor:
        if filtered_book_results != [] and filtered_book_results[0] != '':
            for book_id in filtered_book_results:
                book_info = get_book_details(book_id)
                cursor.execute("SELECT username FROM users WHERE user_id = %s", (book_info[1],))
                username = cursor.fetchone()[0]
                book_info.append(username)
                book_results.append(book_info)

    user_query_results = get_user_id_results(search_query)
    user_results = []
    if user_query_results != [] and user_query_results[0] != '':
        for user_id in user_query_results:
            user_info = get_user_details(user_id)
            user_results.append(user_info)

    current_user = get_current_user()
    return render_template("search.html", search=search_query, current_user=current_user, logged_in=logged_in, book_results=book_results, user_results=user_results)

# USER RELATED APIs
@app.route("/api/adduser", methods=["POST"])
def adduser():
    username = request.form.get('stacked-name')
    bio = request.form.get('stacked-bio')
    email = request.form.get('email')

    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO users 
            (username, bio, email, published_books, library_books) 
            VALUES (%s, %s, %s, %s, %s)
        """, (username, bio, email, '', ''))

    return redirect(f"/home/{username}")


