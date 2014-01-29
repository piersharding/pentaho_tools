#!/usr/bin/env python
"""
pentaho_saiku_adhoc_run
------------------------


This program takes the source name of a stored Saiku Adhoc query report or
a Saiku Analytics query and generates either the PDF, XLS or CSV output as requested.

SYNOPSIS:

process query:

  python pentaho_saiku_adhoc_run.py --help

  python pentaho_saiku_adhoc_run.py --url='http://localhost:8080/pentaho' --user='admin' --passwd='admin' --name=test-adhoc.adhoc --solution=a-solution --path=a-path


Copyright (C) Piers Harding 2014 and beyond, All rights reserved

pentaho_saiku_adhoc_run.py is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

"""


import sys, os
import re
from optparse import OptionParser, SUPPRESS_HELP
import logging
from datetime import datetime
import time
import itertools
import requests
import json
import uuid


# main of application
def main():

    parser = OptionParser()
    parser.add_option("-n", "--name", dest="query_name", default=None, type="string",
                          help="A Saiku Adhoc query file name", metavar="QUERY_NAME")
    parser.add_option("-s", "--solution", dest="solution", default=None, type="string",
                          help="Solution directory of A Saiku Adhoc query file name", metavar="SOLUTION")
    parser.add_option("-f", "--path", dest="path", default=None, type="string",
                          help="Path to A Saiku Adhoc query file name", metavar="PATH")
    parser.add_option("-u", "--user", dest="user", default=None, type="string",
                              help="Pentaho user name", metavar="USER")
    parser.add_option("-p", "--passwd", dest="passwd", default=None, type="string",
                          help="Pentaho user password", metavar="PASSWD")
    parser.add_option("-l", "--url", dest="url", default=None, type="string",
                          help="Pentaho host URL", metavar="URL")
    parser.add_option("-t", "--type", dest="output_type", default='pdf', type="string",
                          help="Report output type - csv, xls or pdf", metavar="URL")
    parser.add_option("-g", "--generate", dest="generate_file", default=False, action="store_true",
                  help="Generate file and write filename to stdout", metavar="GENERATE_FILE")
    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true",
                  help="Switch on debugging", metavar="DEBUG")
    (options, args) = parser.parse_args()

    # f = open('/tmp/rep.log', 'w')
    # f.write("options are: " + str(options))
    # f.close()

    # setup logging
    if options.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    if options.query_name == None or options.url == None or options.user == None or options.passwd == None :
        logging.error("Minimum paramters not supplied: url, name, solution, user, passwd")
        sys.exit(1)

    # set default to adhoc queries
    if not re.match(r'^.*?\.\w+$', options.query_name) :
        options.query_name = options.query_name + '.adhoc'

    if not re.match(r'^.*?\.(adhoc|saiku)$', options.query_name) :
        logging.error("Query name (%s) must be the repository file and end in either .adhoc or .saiku" % options.query_name)
        sys.exit(1)

    rep_type = options.query_name.split('.')[-1]

    if not options.output_type == 'csv' and not options.output_type == 'xls' and not options.output_type == 'pdf':
        logging.error("Type must be xls, csv or pdf")
        sys.exit(1)


    logging.debug("options are: " + str(options))

    if options.path == None:
        options.path = ""

    if options.solution == None:
        options.solution = ""

    # set the encoding to stop errors on the input/putput streams
    reload(sys)
    sys.setdefaultencoding("utf-8")

    rep_uuid = str(uuid.uuid1()).upper()

    if rep_type == 'adhoc' :
        # look up the report definition
        definition_url = options.url + "/content/saiku-adhoc/rest/repository/query/" + \
            options.query_name + "?name=" + options.query_name + \
            "&solution=" + str(options.solution) + "&path=" + str(options.path) + \
            "&action=" + options.query_name + \
            "&userid=" + options.user + "&password=" + options.passwd

        headers = {'content-type': 'application/json',
                   'accept': 'application/json, text/javascript, */*; q=0.01'}
        res = requests.get(definition_url, headers=headers)
        if not res.status_code == 200:
            logging.error("Call to lookup report failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        logging.debug("content: " + res.text)
        # payload = json.loads(res.text)

        # create the report instance
        payload = re.sub(r'"name":".*?",', '', res.content, 1)
        for t in ["newname", 'lastModified', 'solution', 'action', 'path']:
            payload = re.sub(r'"' + t + '":.*?,', '', payload, 1)
        payload = re.sub(r',"overwrite":.*?}', '}', payload, 1)
        logging.debug("json: " + str(payload))

        create_url = options.url + "/content/saiku-adhoc/rest/query/" + rep_uuid + \
            "?userid=" + options.user + "&password=" + options.passwd
        res = requests.post(create_url, headers=headers, data=payload)
        if not res.status_code == 200:
            logging.error("Call to create report instance failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        # logging.debug("content: " + res.text)

        # run the report
        report_url = options.url + "/content/saiku-adhoc/rest/query/" + rep_uuid + \
            "/report/1?_=" + str(int(time.time())) + \
            "&userid=" + options.user + "&password=" + options.passwd

        headers = {}
        res = requests.get(report_url, headers=headers)
        if not res.status_code == 200:
            logging.error("Call to run report failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        # logging.debug("content: " + res.text)

        # Now generate the requested output type
        report_url = options.url + "/content/saiku-adhoc/rest/export/" + rep_uuid + \
            "/" + options.output_type + \
            "?userid=" + options.user + "&password=" + options.passwd

        headers = {}
        res = requests.get(report_url, headers=headers)
        if not res.status_code == 200:
            logging.error("Call to run report failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        logging.debug("result: " + res.text)

        if options.generate_file:
            report_file = '/tmp/' + re.sub(r'%..', '', re.sub(r'.*?\/', '', options.query_name)) + '-' + time.strftime('%Y%m%d-%H%M%S', time.gmtime()) + '.' + options.output_type
            # report_file = '/tmp/' + rep_uuid + '.' + options.output_type
            f = open(report_file, 'w')
            f.write(res.content)
            f.close()
            print(report_file)
        else:
            print(res.content)

    else:
        # saiku analytics queries
        # look up the report definition
        filename = ""
        if len(str(options.solution)) > 0:
            filename = options.solution + '%2F'
        filename += options.query_name
        definition_url = options.url + "/content/saiku/admin/pentahorepository2/resource?file=" + filename + \
            "&userid=" + options.user + "&password=" + options.passwd

        headers = {'content-type': 'application/x-www-form-urlencoded',
                   'accept': 'text/plain, */*; q=0.01'}
        res = requests.get(definition_url, headers=headers)
        if not res.status_code == 200:
            logging.error("Call to lookup report failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        logging.debug("content: " + res.text)

        # create the report instance
        payload = {'xml': res.text, 'formatter': 'flattened', 'type': 'QM'}
        logging.debug("parameters: " + str(payload))

        headers = {'content-type': 'application/x-www-form-urlencoded',
                   'accept': 'application/json, text/javascript, */*; q=0.01'}
        create_url = options.url + "/content/saiku/admin/query/" + rep_uuid + \
            "?userid=" + options.user + "&password=" + options.passwd
        res = requests.post(create_url, headers=headers, data=payload)
        if not res.status_code == 200:
            logging.error("Call to create report instance failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        logging.debug("content: " + res.text)

        # Now generate the requested output type
        report_url = options.url + "/content/saiku/admin/query/" + rep_uuid + \
            "/result/flattened?limit=0&_=" + str(int(time.time())) + \
            "&userid=" + options.user + "&password=" + options.passwd

        headers = {}
        res = requests.get(report_url, headers=headers)
        if not res.status_code == 200:
            logging.error("Call to run report failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        logging.debug("content: " + res.text)

        # Now generate the requested output type
        report_url = options.url + "/content/saiku/admin/query/" + rep_uuid + \
            "/export/" + options.output_type + \
            "/flattened?userid=" + options.user + "&password=" + options.passwd

        headers = {}
        res = requests.get(report_url, headers=headers)
        if not res.status_code == 200:
            logging.error("Call to run report failed: " + str(res.status_code) + ": " + str(res.reason))
            sys.exit(1)
        logging.debug("result: " + res.text)

        if options.generate_file:
            report_file = '/tmp/' + re.sub(r'%..', '', re.sub(r'.*?\/', '', options.query_name)) + '-' + time.strftime('%Y%m%d-%H%M%S', time.gmtime()) + '.' + options.output_type
            # report_file = '/tmp/' + rep_uuid + '.' + options.output_type
            f = open(report_file, 'w')
            f.write(res.content)
            f.close()
            print(report_file)
        else:
            print(res.content)

    sys.exit(0)


# ------ Good Ol' main ------
if __name__ == "__main__":
    main()

