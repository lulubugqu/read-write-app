# server.py
from flask import Flask, render_template, request

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

@app.route("/")
def home():
    return render_template("home.html")
