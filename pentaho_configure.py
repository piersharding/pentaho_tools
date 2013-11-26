#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reconfigure a Pentaho instance
==============================

This program takes a Python cfg file as input and updates all the instance dependent config
In the Pentaho installation

SYNOPSIS:

process Pentaho config:

  python pentaho_configure.py --help

  python pentaho_configure.py --cfg '/file/pentaho_environment.cfg' --base='/pentaho/install/base' --only-xmi --debug


pentaho.cfg file example:
[CONNECTION]
hibernate: mysql://root:letmein@localhost:3306/hibernate

[oti/metadata.xmi]
DATABASE_SERVER: server.name
DATABASE_TYPE: MYSQL
DATABASE_ACCESS: Native
DATABASE_DATABASE: db
DATABASE_PORT: 3306
DATABASE_USERNAME: user
DATABASE_PASSWORD: password
DATABASE_JDBC_URL: jdbc:mysql://server.namem:3306/db?defaultFetchSize=500&amp;useCursorFetch=true

[spring_xml]
xml:  <bean id="dataSource" class="org.springframework.jdbc.datasource.DriverManagerDataSource">
    <property name="driverClassName" value="com.mysql.jdbc.Driver" />
    <property name="url" value="jdbc:mysql://server.name:3306/hibernate" />
    <property name="username" value="user" />
    <property name="password" value="password" />
  </bean>


[mysql_hibernate]
connection.driver_class: com.mysql.jdbc.Driver
connection.url: jdbc:mysql://server.name:3306/hibernate
dialect: org.hibernate.dialect.MySQL5InnoDBDialect
connection.username: user
connection.password: password
connection.pool_size: 10
show_sql: false

[spring_properties]
jdbc.driver: com.mysql.jdbc.Driver
jdbc.url: jdbc:mysql://server.name:3306/hibernate
jdbc.username: user
jdbc.password: password
hibernate.dialect: org.hibernate.dialect.MySQLDialect

[jdbc_properties]
datasource[0]: Hibernate/type=javax.sql.DataSource
    Hibernate/driver=com.mysql.jdbc.Driver
    Hibernate/url=jdbc:mysql://server.name:3306/hibernate
    Hibernate/user=user
    Hibernate/password=password
datasource[1]: Quartz/type=javax.sql.DataSource
    Quartz/driver=com.mysql.jdbc.Driver
    Quartz/url=jdbc:mysql://server.name:3306/quartz
    Quartz/user=user
    Quartz/password=password
datasource[2]: OTI_BI/type=javax.sql.DataSource
    A_DATASOURCE/driver=com.mysql.jdbc.Driver
    A_DATASOURCE/url=jdbc:mysql://server.name:3306/a_db
    A_DATASOURCE/user=user
    A_DATASOURCE/password=password

[tomcat]
xml: <?xml version="1.0" encoding="UTF-8"?>
    <Context path="/pentaho" docbase="webapps/pentaho/">
    <Resource name="jdbc/Hibernate" auth="Container" type="javax.sql.DataSource"
    factory="org.apache.commons.dbcp.BasicDataSourceFactory" maxActive="20" maxIdle="5"
    maxWait="10000" username="user" password="password"
    driverClassName="com.mysql.jdbc.Driver" url="jdbc:mysql://server.name:3306/hibernate"
    validationQuery="select 1" />
    <Resource name="jdbc/Quartz" auth="Container" type="javax.sql.DataSource"
    factory="org.apache.commons.dbcp.BasicDataSourceFactory" maxActive="20" maxIdle="5"
    maxWait="10000" username="user" password="password"
    driverClassName="com.mysql.jdbc.Driver" url="jdbc:mysql://server.name:3306/quartz"
    validationQuery="select 1"/>
    </Context>

[datasources]
xml: <DataSources>
    <DataSource>
    <DataSourceName>Provider=Mondrian;DataSource=Pentaho</DataSourceName>
    <DataSourceDescription>Pentaho BI Platform Datasources</DataSourceDescription>
    <URL>http://localhost:8080/pentaho/Xmla?userid=user&amp;password=password</URL>
    <DataSourceInfo>Provider=mondrian</DataSourceInfo>
    <ProviderName>PentahoXMLA</ProviderName>
    <ProviderType>MDP</ProviderType>
    <AuthenticationMode>Unauthenticated</AuthenticationMode>
    <Catalogs>
      <Catalog name="A catalog name">
        <DataSourceInfo>Provider=mondrian;DataSource=A_DATASOURCE</DataSourceInfo>
        <Definition>solution:/a/path/to.a.Schema.xml</Definition>
      </Catalog>
    </Catalogs>
    </DataSource>
    </DataSources>

[kettle]
xml: <kettle-repository>
    <repositories.xml.file></repositories.xml.file>
    <repository.type>rdbms</repository.type>
    <repository.name>A_REPO</repository.name>
    <repository.userid>admin</repository.userid>
    <repository.password>admin</repository.password>
    </kettle-repository>

[hibernate0]
name: Moodle
maxactconn: 0
driverclass: com.mysql.jdbc.Driver
idleconn: 0
username: root
password: letmein
url: jdbc:mysql://localhost:3306/moodle_oua
wait: 0
query:



Copyright (C) Piers Harding 2013 and beyond, All rights reserved

pentaho_configure.py is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

"""

import sys, os
import ConfigParser
import re
from optparse import OptionParser, SUPPRESS_HELP
import logging
import datetime
import base64

test_mode = False

NOW = datetime.datetime.now().strftime('%Y.%m.%d-%H%M%S')

import sqlalchemy as db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.mysql import BIT
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class DDatasource(Base):
    __tablename__ = 'DATASOURCE'
    NAME = db.Column(db.String(50), primary_key=True)
    MAXACTCONN = db.Column(db.Integer())
    DRIVERCLASS = db.Column(db.String(50), unique=False)
    IDLECONN = db.Column(db.Integer())
    USERNAME = db.Column(db.String(50), unique=False)
    PASSWORD = db.Column(db.String(150), unique=False)
    URL = db.Column(db.String(512), unique=False)
    QUERY = db.Column(db.String(100), unique=False)
    WAIT = db.Column(db.Integer())

    def __init__(self, name):
        self.NAME = name

    def __repr__(self):
        return '<DATASOURCE %r, driver: %s, maxactconn: %d, %s, username: %s, password: %s, url: %s>' % (self.NAME,
                       self.DRIVERCLASS, self.MAXACTCONN, self.USERNAME, self.PASSWORD, self.URL)


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


# main of application
def main():

    # Files that will be reconfigured
   #  '': 'pentaho-solutions/oti/metadata.xmi',
    config_files = {
    'tomcat': 'tomcat/webapps/pentaho/META-INF/context.xml',
    'spring_xml': 'pentaho-solutions/system/applicationContext-spring-security-jdbc.xml',
    'mysql_hibernate': 'pentaho-solutions/system/hibernate/mysql5.hibernate.cfg.xml',
    'spring_properties': 'pentaho-solutions/system/applicationContext-spring-security-hibernate.properties',
    'jdbc_properties': 'pentaho-solutions/system/simple-jndi/jdbc.properties',
    'datasources': 'pentaho-solutions/system/olap/datasources.xml',
    'kettle': 'pentaho-solutions/system/kettle/settings.xml',
    }

    parser = OptionParser()
    parser.add_option("-c", "--cfg", dest="cfg_file", default=None, type="string",
                          help=".cfg file to configure Pentaho environment", metavar="CFG_FILE")
    parser.add_option("-b", "--base", dest="base_dir", default=None, type="string",
                          help="Pentaho base installation directory", metavar="BASE_DIR")
    parser.add_option("-x", "--only-xmi", dest="only_xmi", default=False, action="store_true",
                      help="Only process XMI files", metavar="XMI")
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

    if options.cfg_file == None or options.base_dir == None:
        logging.error("Must supply config file and base directory")
        sys.exit(1)

    if options.cfg_file[0] == "~":
        options.cfg_file = os.path.expanduser(options.cfg_file)
    if options.base_dir[0] == "~":
        options.base_dir = os.path.expanduser(options.base_dir).rstrip('/')

    # load the cfg file
    logging.debug('checking for cfg file: ' + options.cfg_file)
    if not os.path.isfile(options.cfg_file):
        logging.error("cfg file not found: " + str(options.cfg_file))
        sys.exit(1)

    if options.test:
        test_mode = True
        logging.info("Test mode - read only")

    fh = open(options.cfg_file, 'rb')
    cr = ConfigParser.ConfigParser()
    cr.readfp(fh)
    fh.close()


    SQLALCHEMY_DATABASE_URI = ""
    config = {'hibernate': {}}
    for s in cr.sections():
        logging.debug('section: ' + s + ' - ' + repr(cr.items(s)))
        c = {}
        for k, v in cr.items(s):
            c[k] = v
        if s == 'CONNECTION':
            SQLALCHEMY_DATABASE_URI = cr.get(s, 'hibernate')
        elif s.endswith('.xmi'):
            sk = options.base_dir + '/pentaho-solutions/' + s.lstrip('/')
            config[sk] = c
        elif s.startswith('hibernate'):
            config['hibernate'][c['name']] = c
        else:
            config[s] = c

    logging.debug('config loaded: ' + repr(config))

    # connect up to the Kettle repository
    engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # does the install directory exist
    logging.debug('checking for base directory: ' + options.base_dir)
    if not os.path.isdir(options.base_dir):
        logging.error("base install directory not found: " + str(options.base_dir))
        sys.exit(1)

    # does the install directory have a tomcat dir
    logging.debug('checking for tomcat')
    if not os.path.isdir(options.base_dir + "/tomcat"):
        logging.error("base install directory does not have a tomcat dir: " + str(options.base_dir))
        sys.exit(1)

    # does the target files exist
    for s, f in config_files.iteritems():
        logging.debug('checking configuration file exists: ' + f)
        if not os.path.isfile(options.base_dir + '/' + f):
            logging.error("configuration file not found: " + str(f))
            sys.exit(1)

    # search for XMI files
    existing_xmi = []
    for root, dirs, files in os.walk(options.base_dir):
        for file in files:
            if file.endswith(".xmi"):
                file = os.path.join(root, file)
                if file in config:
                    # process XMI
                    existing_xmi.append(file)
                else:
                    file = file[file.find('pentaho-solutions/')+len('pentaho-solutions/'):]
                    logging.warn("configuration missing for XMI: " + str(file))

    logging.debug('existing xmi files for processing: ' + repr(existing_xmi))


    # backup core config sections
    if not options.only_xmi:
        logging.info('Processing all config')
        for f in config_files.values():
            backup_file(options.base_dir + '/' + f)
    else:
        logging.info('Processing only XMI')

    # backup XMI files
    for f in existing_xmi:
        backup_file(f)

    if not options.only_xmi:
        # update hibernate datasources
        session.query(DDatasource).delete()
        if options.test:
            session.rollback()
        else:
            session.commit()
        for k, hib in config['hibernate'].iteritems():
            h = DDatasource(k)
            h.MAXACTCONN = hib['maxactconn']
            h.DRIVERCLASS = hib['driverclass']
            h.IDLECONN = hib['idleconn']
            h.USERNAME = hib['username']
            h.PASSWORD = base64.b64encode(hib['password'])
            h.URL = hib['url']
            h.QUERY = hib['query']
            h.WAIT = hib['wait']
            session.add(h)
        if options.test:
            session.rollback()
        else:
            session.commit()


        # overwrite tomcat config
        tomcat = options.base_dir + '/' + config_files['tomcat']
        output_file(tomcat, config['tomcat']['xml'] + "\n")

        # update spring bean config
        spring_xml = options.base_dir + '/' + config_files['spring_xml']
        contents = "".join(open(spring_xml, 'rb').readlines())
        contents = re.sub('<bean id="dataSource".*?<\/bean>', config['spring_xml']['xml'], contents, 1, re.S)
        output_file(spring_xml, contents + "\n")

        # update hibernate config
        mysql_hibernate = options.base_dir + '/' + config_files['mysql_hibernate']
        contents = "".join(open(mysql_hibernate, 'rb').readlines())
        for k, v in config['mysql_hibernate'].iteritems():
            contents = re.sub('<property name="' + k + '">.*?</property>', '<property name="' + k + '">' + v + '</property>', contents, 1, re.S)
        output_file(mysql_hibernate, contents)

        # udate spring hibernate properties
        spring_properties = options.base_dir + '/' + config_files['spring_properties']
        contents = ""
        for k, v in config['spring_properties'].iteritems():
            contents = contents + k + '=' + v + "\n"
        output_file(spring_properties, contents + "\n")

        # update jdbc properties config
        jdbc_properties = options.base_dir + '/' + config_files['jdbc_properties']
        contents = ""
        for k, v in config['jdbc_properties'].iteritems():
            contents = contents + v + "\n"
        output_file(jdbc_properties, contents + "\n")


        # update datasources config
        kettle = options.base_dir + '/' + config_files['kettle']
        contents = config['kettle']['xml'] + "\n"
        output_file(kettle, contents)


        # update kettle settings config
        datasources = options.base_dir + '/' + config_files['datasources']
        contents = '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + config['datasources']['xml'] + "\n"
        output_file(datasources, contents)


    # find all *.xmi files in configand do substitutions
    for e in existing_xmi:
        contents = "".join(open(e, 'rb').readlines())
        # logging.debug('updating XMI: ' + e + ': ' + repr(config[f]))
        for k, v in config[f].iteritems():
            k = k.upper()
            # logging.debug('replacing: ' + k + ' with: ' + v)
            contents = re.sub('(<CWM:TaggedValue xmi.id = \'(\\w+)\' tag = \'' + k + '\' value = \'.*?\'\\s*?\/>)',
                              "<CWM:TaggedValue xmi.id = '\\2' tag = '" + k + "' value = '" + v + "'/>", contents, 1)
        output_file(f, contents)

    logging.info('Finished')
    sys.exit(0)



# ------ Good Ol' main ------
if __name__ == "__main__":
    main()

