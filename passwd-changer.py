# -*- coding: utf-8 -*-
"""
Password Changer
===================
This is a small application that provides a password changer for
Pentaho users

"""
from flask import Flask, request, render_template, redirect, url_for, flash
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUserMixin,
                            confirm_login, fresh_login_required)
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import BIT
import base64

class User(UserMixin):
    def __init__(self, name, fullname, active=True):
        self.name = name
        self.fullname = fullname
        self.id = name
        self.active = active

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

from flask import Flask


class Anonymous(AnonymousUserMixin):
    name = u"Anonymous"


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:letmein@localhost/hibernate'


db = SQLAlchemy(app)

class DBUser(db.Model):
    __tablename__ = 'USERS'
    USERNAME = db.Column(db.String(50), primary_key=True)
    PASSWORD = db.Column(db.String(50), unique=False)
    DESCRIPTION = db.Column(db.String(120), unique=False)
    ENABLED = db.Column(BIT(1))

    def __init__(self, username, password, description):
        self.USERNAME = username
        self.PASSWORD = password
        self.DESCRIPTION = description

    def __repr__(self):
        return '<User %r>' % self.USERNAME


SECRET_KEY = "yeah, not actually a secret"
DEBUG = True

app.config.from_object(__name__)

login_manager = LoginManager()

login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."
login_manager.refresh_view = "reauth"

@login_manager.user_loader
def load_user(username):
    u = DBUser.query.get(username)
    return User(u.USERNAME, u.DESCRIPTION)


login_manager.setup_app(app)

@app.route("/")
@fresh_login_required
def index():
    return render_template("pcindex.html")


@app.route("/changepasswd", methods=["GET", "POST"])
@fresh_login_required
def changepasswd():
    print(current_user.id)
    if request.method == "POST" and "password" in request.form:
        password = request.form["password"]
        new1 = request.form["new1"]
        new2 = request.form["new2"]
        u = DBUser.query.get(current_user.id)
        if u and u.PASSWORD == base64.b64encode(password):
            # user is logged in and old password is correct
            if new1 == new2 and len(new1) > 5:
                # we can now change the password
                u.PASSWORD = base64.b64encode(new1)
                db.session.commit()
                flash("Password changed!")
                return redirect(url_for("index"))
            else:
                flash("Sorry, but you could not change your password.  Please try again.")
        else:
            flash(u"Invalid old password.")
    return render_template("changepasswd.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and "username" in request.form:
        username = request.form["username"]
        password = request.form["password"]
        u = DBUser.query.get(username)
        if u and u.PASSWORD == base64.b64encode(password):
            remember = request.form.get("remember", "no") == "yes"
            if login_user(User(u.USERNAME, u.DESCRIPTION), remember=remember):
                flash("Logged in!")
                return redirect(request.args.get("next") or url_for("index"))
            else:
                flash("Sorry, but you could not log in.")
        else:
            flash(u"Invalid username.")
    return render_template("login.html")


@app.route("/reauth", methods=["GET", "POST"])
@login_required
def reauth():
    if request.method == "POST":
        confirm_login()
        flash(u"Reauthenticated.")
        return redirect(request.args.get("next") or url_for("index"))
    return render_template("reauth.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run()

application = app
