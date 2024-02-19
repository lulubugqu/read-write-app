# server.py
# 📁 server.py -----

from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth


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

# 👆 We're continuing from the steps above. Append this to your server.py file.

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )



# 👆 We're continuing from the steps above. Append this to your server.py file.

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

# 👆 We're continuing from the steps above. Append this to your server.py file.

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

## STORY EDITING PAGES - OVERVIEW AND WRITING PAGE

@app.route("/myworks/<book_id>", method=["GET"])    #(STORY OVERVIEW PAGE)
# this is a page where the user can customize their book details. I.E., title, image, summary, genre, tags, etc. They can also create a new chapter, edit a chapter, etc. If the book already exists, the info will be prefilled from database. If not, the form is just empty. 

@app.route("/myworks/<book_id>/<chapter_id>", method=["GET"])   #(EDITING CHAPTER PAGE)
# this is similar to the story page Shriya made, but it can edit the text and save to publish the chapter. If the chapter is new, it'll already be in the database but with empty content. SO either way, just display the content.  

# APIs for story overview and writing page
@app.route("/myworks/api/newbook", method=["POST"])
# this is where the form gets sent when its submitted
# creates a new book with the data from the form. Called when the user clicks "create a new story" from their profile. When that button is clicked, we are redirected to 
# /myworks/<book_id> with the new book id made. Chapter 1 should be made, with empty content. 

@app.route("/myworks/api/<book_id>/updatebook", method=["PUT"])
# updates the details of the book. Called when the user clicks "save" on the /myworks/<book_id> page. 

@app.route("/myworks/api/<book_id>/<chapter_id>/createchapter", method=["POST"])
# creates a chapter with empty content. called when "+ chapter" is pressed on the myworks/<book_id> book details page.

@app.route("/myworks/api/<book_id>/<chapter_id>/updatechapter", method=["PUT"])
# update chapter in DB with content from /myworks/<book_id>/<chapter_id> editing page.
# called with "save" is clicked in the chapter editing page.

@app.route("/myworks/api/<book_id>/delete", method=["DELETE"])
# book is deleted from database. 
# called when "delete" is clicked on the story detail page. 

@app.route("/myworks/api/<book_id>/<chapter_id>/delete", method=["DELETE"])
# this can be done last, we don't need it. 
# book chapter is deleted from database. 
# called when "delete" chpater is clicked from the story detail page. 

# Need to add more later !!!
@app.route("/search/", methods=["GET"])
@app.route("/search", methods=["GET"])
def search():
    print("search")
    print(request.query_string)
    search = request.args.get('query')
    print(search)

    return render_template("search.html", search=search)