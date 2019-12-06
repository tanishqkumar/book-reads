# GOODREADS CLONE

import os
from flask import Flask, session, redirect, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import urllib.parse
from functools import wraps
import requests

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# initialising the login required functionality
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# starting to build out the web app
@app.route("/")
@login_required
def index():
    return redirect("/search")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    if request.method=="GET":
        return render_template("search.html")
    #search functionality
    if request.method=="POST":
        query = request.form.get("query").lower()
        matches = []
        matches = db.execute(f"SELECT * FROM books WHERE (isbn LIKE ('%{query}%') OR LOWER(title) LIKE ('%{query}%') OR LOWER(author) LIKE ('%{query}%') OR LOWER(year) LIKE ('%{query}%'))").fetchall()
        if matches == []:
            return "There were no results that matched your query."
        return render_template("matches.html", matches=matches)

# make a new /api/<isbn> route that takes GET requests and returns JSONs for other peoples' use
@app.route("/api/<isbn>")
def api(isbn):
    bookInfo = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
    if bookInfo == None:
        return ("Book not found in database. Try another ISBN.")
    else:
        review_count = db.execute("SELECT COUNT(*) FROM reviews WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
        average_score = db.execute("SELECT AVG(rating) FROM reviews WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
        return jsonify({"title": bookInfo['title'], "author": bookInfo['author'], "year": bookInfo['year'], "isbn": isbn, "review_count": review_count[0], "average_score": average_score[0]})

@app.route("/book/<isbn>", methods=["GET", "POST"])
@login_required
def book(isbn):
    if request.method == "GET":
        bookInfo = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
        response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "wdEMbZwCMgj17LJQZ0mEiw", "isbns": isbn}).json()
        noRatings = response['books'][0]['work_ratings_count']
        avgRating = response['books'][0]['average_rating']
        bookReviews = db.execute("SELECT * FROM reviews, users WHERE isbn=:isbn AND reviews.user_id=users.id", {"isbn": isbn}).fetchall()
        # in the case that we mistakenly don't have information for that book in the database
        if len(bookInfo) == 0:
            return "Sorry, we don't have any information for that book."
        else:
            return render_template("layout2.html", bookInfo=bookInfo, noRatings=noRatings, avgRating=avgRating, bookReviews=bookReviews)

    if request.method == "POST":
        existing = db.execute("SELECT * FROM reviews WHERE user_id=:id AND isbn=:isbn", {"id": session["user_id"], "isbn": isbn}).fetchall()
        if existing != []:
            return "Sorry--you can only submit one review per book, and you've already submitted a review."
        else:
            review = request.form.get("review")
            rating = request.form.get("rating")
            if not rating or not review:
                return "Please fill out the rating and review before submitting your opinion."
            db.execute("INSERT INTO reviews VALUES (:isbn, :user_id, :review, :rating)", {"isbn": isbn, "user_id": session["user_id"], "review": review, "rating": rating })
            db.commit()
            # redirect to the same page after form submission
            return redirect("/book/%s" %(isbn))


@app.route("/login", methods=["GET", "POST"])
def login():
    # logs anyone who is logged in out automatically
    session.clear()

    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        # we want to take in their login info from the form they post and then query the users database
        username = request.form.get("username")
        password = request.form.get("password")

        matches = db.execute("SELECT * FROM users WHERE username=:username AND password=:password", {"username": username, "password": password}).fetchall()
        if len(matches) != 1:
            return ("Wrong username and/or Password", 404)
        else:
            session["user_id"] = matches[0]["id"]
            return render_template("search.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method=="GET":
        return render_template("register.html")

    else:
        #confirm the passwords match and that the username isn't taken by querying the users table
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation or password != confirmation:
            return ("Fill out all fields and make sure passwords match!", 404)

        existing = db.execute("SELECT * FROM users WHERE (username=:username)", {"username": username}).fetchall()
        if existing != []:
            return ("Username taken--please try another one.", 404)
        elif len(username) > 0:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password})
            db.commit()

        existing = db.execute("SELECT * FROM users WHERE (username=:username)", {"username": username}).fetchall()

        # Remember which user has logged in
        session["user_id"] = existing[0]["id"]

        # Redirect user to home page
        return redirect("/")
