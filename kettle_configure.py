#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reconfigure Kettle DB Connections
===================================
This enables Kettle DB connections to be reconfigured on the fly

process Kettle config:

  python kettle_configure.py --help

  python kettle_configure.py --cfg '/file/kettle_environment.cfg' --debug


Example cfg file:
[CONNECTION]
db: mysql://root:letmein@localhost/kettle_oti
repositories: ~/.kettle/repositories.xml
name: OTI Kettle
server: localhost
database: kettle_oti
port: 3306
username: root
password: Encrypted 2be98afc86aa7f2e4cb15ab64d397a6d4
type: MYSQL
access: Native

[DB1]
host_name: localhost
database_name: db2
port: 3306
username: root
password: Encrypted 2be98afc86aa7f2e4cb15ab64d397a6d4

[DB2]
host_name: localhost
database_name: db1
port: 3306
username: root
password: Encrypted 2be98afc86aa7f2e4cb15ab64d397a6d4


"""
import sys, os
import ConfigParser
import re
from optparse import OptionParser, SUPPRESS_HELP
import logging
import datetime

test_mode = False

import sqlalchemy as db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.mysql import BIT
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

NOW = datetime.datetime.now().strftime('%Y.%m.%d-%H%M%S')

# named backup files for config
def backup_file(filename):

    if test_mode:
        return

    logging.debug("backing up to: " + filename + '.' + NOW)
    fho = open(filename + '.' + NOW, 'w')
    fhi = open(filename, 'rb')
    for line in fhi.readlines():
        fho.write(line)
    fho.close()
    fhi.close()


# overwrite a file
def output_file(filename, contents):

    if test_mode:
        return

    logging.debug("output to: " + filename)
    fho = open(filename, 'w')
    fho.write(contents)
    fho.close()


class DBR_Database(Base):
    __tablename__ = 'R_DATABASE'
    ID_DATABASE = db.Column(db.BigInteger(), primary_key=True)
    NAME = db.Column(db.String(255), primary_key=False, unique=True)
    ID_DATABASE_TYPE = db.Column(db.Integer())
    ID_DATABASE_CONTYPE = db.Column(db.Integer())
    HOST_NAME = db.Column(db.String(255), unique=False)
    DATABASE_NAME = db.Column(db.String(255), unique=False)
    PORT = db.Column(db.Integer())
    USERNAME = db.Column(db.String(255), unique=False)
    PASSWORD = db.Column(db.String(255), unique=False)
    SERVERNAME = db.Column(db.String(255), unique=False)
    DATA_TBS = db.Column(db.String(255), unique=False)
    INDEX_TBS = db.Column(db.String(255), unique=False)

    def __init__(self, name):
        self.NAME = name

    def __repr__(self):
        return '<R_DATABASE %r, host: %s, port: %d, db: %s, username: %s, password: %s>' % (self.NAME,
                       self.HOST_NAME, self.PORT, self.DATABASE_NAME, self.USERNAME, self.PASSWORD)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--cfg", dest="cfg_file", default=None, type="string",
                          help=".cfg file to configure Pentaho environment", metavar="CFG_FILE")
    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true",
                  help="Switch on debugging", metavar="DEBUG")
    parser.add_option("-t", "--test", dest="test", default=False, action="store_true",
              help="Switch on test mode", metavar="TEST")

    (options, args) = parser.parse_args()

    # setup logging
    if options.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    if options.test:
        test_mode = True
        logging.info("Test mode - read only")

    if options.cfg_file == None:
        logging.error("Must supply config file")
        sys.exit(1)

    if options.cfg_file[0] == "~":
        options.cfg_file = os.path.expanduser(options.cfg_file)

    # load the cfg file
    logging.debug('checking for cfg file: ' + options.cfg_file)
    if not os.path.isfile(options.cfg_file):
        logging.error("cfg file not found: " + str(options.cfg_file))
        sys.exit(1)

    fh = open(options.cfg_file, 'rb')
    cr = ConfigParser.ConfigParser()
    cr.readfp(fh)
    fh.close()

    SQLALCHEMY_DATABASE_URI = ""
    repository = None
    config = {}
    for s in cr.sections():
        logging.debug('section: ' + s + ' - ' + repr(cr.items(s)))
        config[s] = {}
        for k, v in cr.items(s):
            config[s][k] = v
        if s == 'CONNECTION':
            SQLALCHEMY_DATABASE_URI = cr.get(s, 'db')
            repository = config[s]
            del config[s]
    logging.debug('config loaded: ' + repr(config))
    logging.debug('repository loaded: ' + repr(repository))

    # check and update repository
    if repository['repositories'][0] == "~":
        repository['repositories'] = os.path.expanduser(repository['repositories'])
    backup_file(repository['repositories'])
    contents = "".join(open(repository['repositories'], 'rb').readlines())
    for k, v in repository.iteritems():
        if not (k == 'db' or k == 'name' or k == 'repositories'):
            logging.debug('searching for: ' + k)
            contents = re.sub('(<connection>.*?<name>' + repository['name'] + '<\/name>.*?<' + k + ').*?(<\/' + k + '>)',
                               '\\1>' + v + '\\2', contents, 1, re.S)
    output_file(repository['repositories'], contents + "\n")

    # connect up to the Kettle repository
    engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()


    # find all database connections and fixup
    for k, section in config.iteritems():
        logging.info('processing: ' + k)
        d = session.query(DBR_Database).filter_by(NAME=k).first()
        logging.debug('DB: ' + repr(d) + ' change to: ' + repr(section))
        d.USERNAME = section['username']
        d.PASSWORD = section['password']
        d.HOST_NAME = section['host_name']
        d.DATABASE_NAME = section['database_name']
        d.PORT = int(section['port'])

        if options.test:
            session.rollback()
        else:
            session.commit()

    logging.info('Updated')
    sys.exit(0)
