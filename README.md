pentaho_tools - admin tools
===========================

Copyright (C) Piers Harding 2013, 1014 - and beyond, All rights reserved

A variety of tools that I've used for integrating and managing Pentaho
    * separate applications for maintaining users and passwords for Pentaho BI Server 4.8
    * PAM authentication module to authenticate users against the Pentaho hibernate database - useful for integration with RStudio Server
    * Pentaho configuration tools for updating data source, schema and metadata config from the command line (alpha)
    * Run Saiku Adhoc reporting queries from the command line and integrate them with Pentaho PDI and/or scheduling and emailing


pentaho_saiku_adhoc_run.py
==========================

Run Saiku Adhoc reports, and Analytics queries (http://meteorite.bi/saiku) from the command line.  Use pentaho_saiku_adhoc_run.py -h to discover the options.  This runs bookmarked (saved) reports by poking the Saiu Adhoc reporting Rest API.

This can be used sample PDI Job/Transformation steps in the /email-saiku directory, and the .xaction example provided shows how reports can be
scheduled from within Pentaho BI 4.8.  Refer to http://www.prashantraju.com/2010/03/emailing-reports-from-the-pentaho-user-console/ for general instructions on setting up schedules and emailing - the emailing for these tools is defined in the PDI job step.


pentaho_user_manager
====================

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


PAM User Authentication
=======================
pentaho_pam.py enables users to authenticate in PAM with their Pentaho user account

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


pentaho_configure.py
====================

Switch config of Pentaho BI server between different .cfg sets - be very careful with this!

kettle_configure.py
===================

Switch config of Pentaho PDI/Kettle between different .cfg sets - be very careful with this!



The pentaho_tools suite is Copyright (c) 2014 - and beyond Piers Harding.
It is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

