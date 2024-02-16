# server.py
# 📁 server.py -----

from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from functools import wraps

import psycopg2, os

from flask import Flask, render_template, request, url_for, flash, redirect, session

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')
app.secret_key = env.get("FLASK_SECRET")

# 👆 We're continuing from the steps above. Append this to your server.py file.

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

def db_connection():
    try:
        connection = psycopg2.connect(os.environ["DATABASE_URL"])
        print ("Success while connecting to PostgreSQL")  
        return connection

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
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

@app.route("/story/<int:storyId>")
def getStory(storyId):
    print("getting story")
    return render_template("story.html")

@app.route("/user")
def getUser():
    # if logged in user is the same as the user request, then set true
    logged_in = True
    print("getting user profile")
    return render_template("user.html", logged_in=logged_in)

# FOR ONCE ACCOUNTS ARE ESTABLISHED
# @app.route("/user/<string:username>")
# def getUser(username):
#     print("getting user profile")
#     return render_template("profile.html")

@app.route("/myworks/new", methods=["POST"])
def newStory():
    print("writing a new story, creates entry in the DB")
    # return render_template("postStory.html")

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