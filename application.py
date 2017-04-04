from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/", methods = ["GET", "POST"])
@login_required
def index():
    #retreive balance
    balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    #retrieve info from transaction db
    stocks = db.execute("SELECT symbol, SUM(num_shares) FROM transactions WHERE user_id=:user_id GROUP BY symbol", user_id = session["user_id"])
    
    #storing user balance in cash
    cash = balance[0]["cash"]
    summary = 0
    
        #loop
    for data in stocks:
        lookup_result = lookup(data["symbol"])
        data["stock"] = lookup_result["name"]
        data["price"] = usd(lookup_result["price"])
        data["num_shares"] = data["SUM(num_shares)"]
        data["total"] = lookup_result["price"] * data["SUM(num_shares)"]
        summary += data["total"]
        data["total"] = usd(data["total"])
    summary += cash
    if request.method == "POST":
        bs_shares = request.form.get("bs_shares")
        symbol_lookup = lookup(request.form.get("symbol"))
        name = symbol_lookup["name"]
        price = symbol_lookup["price"]
        symbols = symbol_lookup["symbol"]
        symbol = symbols.lower()
        #shares = request.form.get("bs_shares")
        #for share in shares:
        if request.form["submit"] == "buy":
            return redirect(url_for("buy", symbol=symbol, bs_shares=bs_shares))
            #return render_template("buy_conf.html", name=name, symbol=symbol_lookup, price=usd(price), bs_shares=bs_shares)
        elif request.form["submit"] == "sell":
            return render_template("sell_conf.html", name=name, price=usd(price), bs_shares=request.form.get("bs_shares"))
        #elif request.method == "GET":
    return render_template("index.html", stocks=stocks, cash=usd(cash), summary=usd(summary))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        #lookup symbol inputted using lookup func in helpers.py
        lookup_result = lookup(request.form.get("symbol"))
        #check stock symbol is valid
        if not lookup_result:
        #if not return apology
            return apology("stock symbol not found")
        #check shares are a valid number
        elif not request.form.get("shares"):
            return apology("please enter the number of shares")
        elif int(request.form.get("shares")) < 1:
            return apology("invalid share number")
        #check stock price * no. shares is not greater than user's cash
        shares = int(request.form.get("shares"))
        #select cash from user's database
        user_cash = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id = session["user_id"])
        #check how much spent by user
        spent = lookup_result["price"] * int(request.form.get("shares"))
        #check not greater than price of shares
        if user_cash[0] ["cash"] < spent:
            return apology("not enough funds")
            
        #update user cash
        update_cash = user_cash[0]["cash"] - spent
        #on first time use insert
        db.execute("INSERT INTO transactions (symbol, stock, num_shares, price, user_id) VALUES(:symbol, :stock, :num_shares, :price, :user_id)", symbol=request.form.get("symbol"), stock = lookup_result["name"], num_shares=request.form.get("shares"), price=lookup_result["price"], user_id=session["user_id"])
        #update cash in db
        db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", cash = update_cash, user_id = session["user_id"])
        return redirect (url_for("index"))
    else:
        symbol=request.args["symbol"]
        bs_shares=request.args["bs_shares"]
        return render_template("buy.html", symbol=symbol, bs_shares=bs_shares)
        

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    transactions = db.execute("SELECT * FROM transactions WHERE user_id=:user_id", user_id=session["user_id"])
    return render_template("history.html", transactions=transactions)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    #lookup symbol inputted using lookup func in helpers.py
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
    #display stock quote template only if valid
    #check stock symbol is valid
        if quote == None:
    #if not return apology
            return apology("stock symbol not found")
        else:
            return render_template("quoted.html", name=quote["name"], symbol=quote["symbol"], price=quote["price"])
    
    #if accessed via GET, go to quote form
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        
        #ensure passwords are both the same
        elif request.form.get("password") != request.form.get("password2"):
            return apology("passwords don't match")
        #if no errors, hash password for security
        else:
            hash = pwd_context.encrypt(request.form.get("password"))
         # query database for username
        result = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if result:
            return apology("username already taken")
        else:
            #add to database
            db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"), hash=hash)
            # store user into session id
            session["user_id"] = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))[0]["id"]
            
            # redirect user to home page
            return redirect(url_for("index"))
    else:
        return render_template("register.html")
            

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
    #lookup symbol inputted using lookup func in helpers.py
        lookup_result = lookup(request.form.get("symbol"))
        #check stock symbol is valid
        if not lookup_result:
        #if not return apology
            return apology("stock symbol not found")
        #check shares are a valid number
        elif not request.form.get("shares"):
            return apology("please enter the number of shares")
        elif int(request.form.get("shares")) < 1:
            return apology("invalid share number")
        #check share number is not greater than amount of shares user has
        shares = int(request.form.get("shares"))
        #check cost of shares to be sold
        sold = shares * lookup_result["price"]
        #select num_shares from user's database
        current_shares = db.execute("SELECT symbol, SUM(num_shares) FROM transactions WHERE user_id=:user_id GROUP BY symbol HAVING symbol=:symbol", user_id = session["user_id"], symbol=request.form.get("symbol"))
        user_cash = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id = session["user_id"])
        #check user has enough shares
        if current_shares[0] ["SUM(num_shares)"] < shares:
            return apology("not enough shares")
            
        #update user cash
        update_cash = user_cash[0]["cash"] + sold
        
        #on first time use insert
        db.execute("INSERT INTO transactions (symbol, stock, num_shares, price, user_id) VALUES(:symbol, :stock, :num_shares, :price, :user_id)", symbol=request.form.get("symbol"), stock = lookup_result["name"], num_shares=(-shares), price=lookup_result["price"], user_id=session["user_id"]
        #update cash in db
        db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", cash = update_cash, user_id = session["user_id"])
        return redirect (url_for("index"))
    else:
        return render_template("sell.html")
        
