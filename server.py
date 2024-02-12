# server.py
import psycopg2, os

from flask import Flask, render_template, request, url_for, flash, redirect

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

def db_connection():
    try:
        connection = psycopg2.connect(os.environ["DATABASE_URL"])
        print ("Success while connecting to PostgreSQL")  
        return connection

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)

@app.route("/")
def launch():
    return render_template("launch.html")

@app.route("/login")
def login():
    print("login")
    # return render_template("login.html")

@app.route("/logout")
def logout():
    print("logout")
    return render_template("launch.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    print("signup")
    # return render_template("signup.html")

@app.route("/home")
def home():
    print("home")
    # return render_template("home.html")

@app.route("/story/<int:storyId>")
def getStory(storyId):
    print("getting story")
    # return render_template("story.html")

@app.route("/user/<string:username>")
def getUser(username):
    print("getting user profile")
    # return render_template("profile.html")

@app.route("/myworks/new", methods=["POST"])
def newStory():
    print("writing a new story, creates entry in the DB")
    # return render_template("postStory.html")

@app.route("/myworks/<int:storyId>/write", methods=["PUT"])
def editStory():
    print("edits story, modifies DB entry")
    # return render_template("editStory.html")

@app.route("/myworks/<int:storyId>/delete", methods=["DELETE"])
def deleteStory():
    print("deletes story, deletes entry in DB")
    # return render_template("deleteStory.html")

# Need to add more later !!!
@app.route("/search")
def search():
    print("search")
    print(request.query_string)
    # return render_template("search.html")