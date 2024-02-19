# server.py
# 📁 server.py -----

from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from functools import wraps
# from flask-session import Session


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
def get_db_cursor(commit=False):
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

# 
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

# @app.route("/login")
# def login():
#     print("login")
#     # return render_template("login.html")

# @app.route("/logout")
# def logout():
#     print("logout")
#     return render_template("launch.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    print("signup")
    # return render_template("signup.html")

@app.route("/home")
def home():
    return render_template("home.html")

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

@app.route("/user")
def getUser():
    # if logged in user is the same as the user request, then set true
    # session=session.get('user')
    # print("session: ")
    # print(session)
    # if 'user' in session:
    #     logged_in = True
    # else:
    #     logged_in = False
    logged_in = True;
    return render_template("user.html", logged_in=logged_in)

# FOR ONCE ACCOUNTS ARE ESTABLISHED
# @app.route("/user/<string:username>")
# def getUser(username):
#     print("getting user profile")
#     return render_template("profile.html")

@app.route("/myworks/new", methods=["GET","POST"])
def newStory():
    print("writing a new story, creates entry in the DB")
    return render_template("storylaunch.html")

@app.route("/myworks/<int:storyId>/write", methods=["PUT"])
def editStory():
    print("edits story, modifies DB entry")
    # return render_template("editStory.html")

@app.route("/myworks/<int:storyId>/edit", methods=["PUT"])
def editChapter():
    print("edits chapter, modifies DB entry")
    return render_template("editChapter.html")

@app.route("/myworks/<int:storyId>/create", methods=["POST"])
def createChapter():
    print("writing a new chapter, creates an entry in the DB")
    return render_template("createChapter.html")

@app.route("/myworks/<int:storyId>/delete", methods=["DELETE"])
def deleteStory():
    print("deletes story, deletes entry in DB")
    # return render_template("deleteStory.html")

# Need to add more later !!!
@app.route("/search/", methods=["GET"])
@app.route("/search", methods=["GET"])
def search():
    print("search")
    print(request.query_string)
    search = request.args.get('query')
    print(search)

    return render_template("search.html", search=search)