#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PAM User Authentication
========================
This enables users to authenticate in PAM with their Pentaho user account

The primary use of this is so Pentaho users can be the same as RStudio Server users

The /etc/pam.d/rstudio config file should look like:

auth requisite pam_succeed_if.so uid >= 500 quiet
auth required pam_exec.so expose_authtok /path/to/pentaho_pam.py
account required pam_unix.so


PAM passes the user details in via environment variables eg:

PAM_USER=piers
PAM_TYPE=auth
PAM_SERVICE=rstudio
PWD=/


The password is passed in on stdin and is terminated with a NULL

UNIX user accounts with the same name as the Pentaho user account must still be created
as this is required for the allocation of UID:GID, and OS quota management
They can be created as non-login accounts though

Change the SQLALCHEMY_DATABASE_URI to the appropriate string for your Pentaho setup

"""
SQLALCHEMY_DATABASE_URI = 'mysql://root:letmein@localhost/hibernate'


import os
import sys
import logging
import re
import base64

import sqlalchemy as db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.mysql import BIT
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
Session = sessionmaker(bind=engine)
session = Session()

class DBUser(Base):
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


SECRET_KEY = "yeah, not actually a secret-less"
DEBUG = True

# we have crazy null characters on the password string
def nullstrip(s):
    """Return a string truncated at the first null character."""
    try:
        s = s[:s.index('\x00')]
    except ValueError:  # No nulls were found, which is okay.
        pass
    return s

if __name__ == "__main__":
    # setup the logger
    logger = logging.getLogger('pentaho_pam')
    hdlr = logging.FileHandler('/tmp/pentaho_pam.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.WARN)
    logger.info('Started pentaho_pam')

    # username must exist in the environment
    if 'PAM_USER' in os.environ:
        username = os.environ['PAM_USER']
    else:
        logger.error('login cannot continue as PAM_USER env var not set')
        sys.exit(1)
    logger.info('username found: ' + username)

    # lookup user
    u = session.query(DBUser).filter_by(USERNAME=username).first()
    logger.info('DB User: ' + repr(u))

    # chcek that user is in passwd file
    found = False
    for line in open("/etc/passwd"):
        if re.search(r'^' + username + ':', line):
            found = True
    if not found:
        logger.error('login cannot continue as user(%s) not found in /etc/passed' % username)
        sys.exit(1)

    # get password from stdin
    password = nullstrip("".join(sys.stdin).strip())
    logger.info('passwd: ' + password + "#")
    logger.info('passwd: ' + str(len(password)) + "#")
    logger.info('passwd: ' + base64.urlsafe_b64encode(password))
    logger.info('db passwd: ' + u.PASSWORD)
    logger.info('enabled: ' + str(u.ENABLED))
    if len(password) < 3:
        logger.error('login cannot continue as user(%s) password not supplied' % username)
        sys.exit(1)

    # check password and enabled flag
    if u:
        if u.PASSWORD == base64.b64encode(password) and \
            str(u.ENABLED) == '1':
            logger.info('login for user: ' + u.USERNAME + " successful")
            sys.exit(0)
        else:
            logger.warn('login for user: ' + u.USERNAME + " failed")
            sys.exit(1)
    else:
            logger.warn('user not found: ' + username)
            sys.exit(1)
