pentaho_user_manager
====================

Copyright (C) Piers Harding 2013 - and beyond, All rights reserved

Pentaho (http://community.pentaho.com/) user management interface - maintain users and ACL groups, and a standalone password changer

Both applications are written using Python Flask http://flask.pocoo.org/ .  They are designed to 
integrate with the MySQL or PostgreSQL backend of Pentaho to administer users in the Hibernate database.

Dependencies are:
Flask (0.10.1)
Flask-Login (0.2.5)
Flask-SQLAlchemy (0.16)

Quick install is:
easy_install flask
easy_install flask-login
easy_install flask-sqlalchemy


Configure each application something like the following (change directory locations as necessary):

  <VirtualHost *:80>
    ServerName pum.local.net

    SetEnv USER piers

    WSGIDaemonProcess yourapplication1 user=piers group=piers threads=5
    WSGIScriptAlias /um /home/piers/code/python/pentaho_user_manager/user-manager.py

    <Directory /home/pentaho/pentaho_user_manager>
        WSGIProcessGroup yourapplication1
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
    </Directory>
  </VirtualHost>


  <VirtualHost *:80>
    ServerName ppc.local.net

    SetEnv USER piers

    WSGIDaemonProcess yourapplication2 user=piers group=piers threads=5
    WSGIScriptAlias /pc /home/piers/code/python/pentaho_user_manager/passwd-changer.py

    <Directory /home/pentaho/pentaho_user_manager>
        WSGIProcessGroup yourapplication2
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
    </Directory>
  </VirtualHost>

pentaho_user_manager is Copyright (c) 2013 - and beyond Piers Harding.
It is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

