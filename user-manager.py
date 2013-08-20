# -*- coding: utf-8 -*-
"""
User Manager
===================
This is a small application that provides a user manager for
Pentaho users

"""
import flask
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
        self.ENABLED = 1

    def __repr__(self):
        return '<User %r>' % self.USERNAME


class DBGrantedAuthorities(db.Model):
    __tablename__ = 'GRANTED_AUTHORITIES'
    USERNAME = db.Column(db.String(50), primary_key=True)
    AUTHORITY = db.Column(db.String(50), primary_key=True)

    def __init__(self, username, authority):
        self.USERNAME = username
        self.AUTHORITY = authority

    def __repr__(self):
        return '<User %r Group %r>' % (self.USERNAME, self.AUTHORITY)


class DBAuthorities(db.Model):
    __tablename__ = 'AUTHORITIES'
    AUTHORITY = db.Column(db.String(50), primary_key=True)
    DESCRIPTION = db.Column(db.String(100), unique=False)

    def __init__(self, authority, description):
        self.AUTHORITY = authority
        self.DESCRIPTION = description

    def __repr__(self):
        return '<Authority %r description %r>' % (self.AUTHORITY, self.DESCRIPTION)



SECRET_KEY = "yeah, not actually a secret-less"
DEBUG = True

app.config.from_object(__name__)

login_manager = LoginManager()

login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"
login_manager.login_message = u""
login_manager.refresh_view = "reauth"

@login_manager.user_loader
def load_user(username):
    u = DBUser.query.get(username)
    return User(u.USERNAME, u.DESCRIPTION)


login_manager.setup_app(app)

@app.route("/")
@fresh_login_required
def index():
    return render_template("index.html")


@app.route('/groups')
@fresh_login_required
def groups():
    groups = DBAuthorities.query.all()
    return render_template('show_groups.html', groups=groups)

@app.route('/add_group', methods=['POST'])
@fresh_login_required
def add_group():
    group = request.form["group"]
    description = request.form["description"]
    if len(group) < 3 or len(description) < 3:
        flash('Invalid group specification')
    else:
        g = DBAuthorities.query.get(group)
        if g:
            flash('Group %s allready exist' % group)
        else:
            g = DBAuthorities(group, description)
            db.session.add(g)
            db.session.commit()
            flash('New group was successfully created')
    return redirect(url_for('groups'))


@app.route('/edit_group/<group>', methods=['GET', 'POST'])
@fresh_login_required
def edit_group(group):
    flask.g.breadcrumb = 'groups'
    g = DBAuthorities.query.get(group)
    if not g:
        flash('Group %s does not exist' % group)
    else:
        if request.method == "GET":
            return render_template('edit_group.html', group=g)
        else:
            if request.form['doit']=='Save':
                g.DESCRIPTION = request.form["description"]
                db.session.commit()
                flash('Group %s saved' % group)
            else:
                flash('Group edit cancelled')
    return redirect(url_for('groups'))


@app.route('/delete_group/<group>', methods=['GET', 'POST'])
@fresh_login_required
def delete_group(group):
    flask.g.breadcrumb = 'groups'
    g = DBAuthorities.query.get(group)
    if not g:
        flash('Group %s does not exist' % group)
    else:
        if request.method == "GET":
            return render_template('delete_group.html', group=g)
        else:
            if request.form['doit']=='Delete':
                db.session.delete(g)
                db.session.commit()
                flash('Group %s deleted' % group)
            else:
                flash('Group delete cancelled')
    return redirect(url_for('groups'))


@app.route('/users')
@fresh_login_required
def users():
    users = DBUser.query.all()
    return render_template('show_users.html', users=users)

@app.route('/delete_user/<user>', methods=['GET', 'POST'])
@fresh_login_required
def delete_user(user):
    flask.g.breadcrumb = 'users'
    u = DBUser.query.get(user)
    if not u:
        flash('User %s does not exist' % user)
    else:
        if request.method == "GET":
            return render_template('delete_user.html', user=u)
        else:
            if request.form['doit']=='Delete':
                for a in DBGrantedAuthorities.query.filter_by(USERNAME=user):
                    db.session.delete(a)
                db.session.delete(u)
                db.session.commit()
                flash('User %s deleted' % user)
            else:
                flash('User delete cancelled')
    return redirect(url_for('users'))


@app.route('/edit_user/<user>', methods=['GET', 'POST'])
@fresh_login_required
def edit_user(user):
    flask.g.breadcrumb = 'users'
    u = DBUser.query.get(user)
    if not u:
        flash('User %s does not exist' % user)
    else:
        if request.method == "GET":
            sql = db.text("SELECT a.AUTHORITY, a.DESCRIPTION, \
                   IF(t.AUTHORITY IS NULL, 0, 1) AS enabled \
                   FROM AUTHORITIES AS a LEFT JOIN \
                    (SELECT AUTHORITY FROM GRANTED_AUTHORITIES WHERE USERNAME = :user ) AS t \
                   ON a.AUTHORITY = t.AUTHORITY")
            groups = db.session.execute(sql, {"user": user}).fetchall()
            return render_template('edit_user.html', user=u, groups=groups)
        else:
            if request.form['doit']=='Save':
                u.DESCRIPTION = request.form["description"]
                if "enabled" in request.form and request.form['enabled'] == 'on':
                    u.ENABLED = 1
                else:
                    u.ENABLED = 0
                new1 = request.form["new1"]
                new2 = request.form["new2"]
                if new1 == new2 and len(new1) > 5:
                    u.PASSWORD = base64.b64encode(new1)
                else:
                    if len(new1) > 0 or len(new2) > 0:
                        flash('Password invalid')
                        return render_template('edit_user.html', user=u)
                for a in DBGrantedAuthorities.query.filter_by(USERNAME=user):
                   db.session.delete(a)
                authorities = request.form.getlist("groups")
                for authority in authorities:
                    a = DBGrantedAuthorities(user, authority)
                    db.session.add(a)
                db.session.commit()
                flash('User %s saved' % user)
            else:
                flash('User edit cancelled')
    return redirect(url_for('users'))


@app.route("/register", methods=["GET", "POST"])
@fresh_login_required
def register():
    flask.g.breadcrumb = 'users'
    user = DBUser("", "", "")
    if request.method == "POST" and "username" in request.form:
        username = request.form["username"]
        description = request.form["description"]
        new1 = request.form["new1"]
        new2 = request.form["new2"]
        user = DBUser(username, base64.b64encode(new1), description)
        if "enabled" in request.form and request.form['enabled'] == 'on':
            user.ENABLED = 1
        else:
            user.ENABLED = 0
        u = DBUser.query.get(username)
        if u:
            flash(u"User allready exists.")
        elif not new1 == new2 or len(new1) <= 5:
            flash("Sorry, password does not match or is too short.  Please try again.")
        elif len(username) < 3:
            flash("Sorry, username invalid.  Please try again.")
        elif len(description) < 3:
            flash("Sorry, description invalid.  Please try again.")
        else:
            db.session.add(user)
            db.session.commit()
            flash("User created! Now set the groups.")
            return redirect(url_for('edit_user', user=user.USERNAME))

    return render_template("register.html", user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and "username" in request.form:
        username = request.form["username"]
        password = request.form["password"]
        u = DBUser.query.get(username)
        sql = db.text("SELECT u.USERNAME, u.DESCRIPTION, u.ENABLED, \
                       IF(t.AUTHORITY IS NULL, 0, 1) AS admin \
                       FROM USERS AS u LEFT JOIN \
                       (SELECT USERNAME, AUTHORITY FROM GRANTED_AUTHORITIES \
                       WHERE USERNAME = :user AND AUTHORITY = 'Admin' ) AS t \
                       ON u.USERNAME = t.USERNAME WHERE u.USERNAME = :user LIMIT 1")
        users = db.session.execute(sql, {"user": username}).fetchall()
        if u and u.PASSWORD == base64.b64encode(password) and \
           users and users[0].admin and users[0].ENABLED == b'\x01':
            remember = request.form.get("remember", "no") == "yes"
            if login_user(User(u.USERNAME, u.DESCRIPTION), remember=remember):
                flash("Logged in!")
                return redirect(request.args.get("next") or url_for("index"))
            else:
                flash("Sorry, but you could not log in.")
        else:
            flash(u"Invalid user.")
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
