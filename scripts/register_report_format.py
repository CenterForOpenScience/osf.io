"""
Register the list of OAuth2 scopes that can be requested by third parties. This populates the Postgres collection
referenced by CAS when responding to authorization grant requests. The database class is minimal; the exact
specification for what a scope contains lives in the python module from which this collection is drawn.
"""

import sys
import logging
import argparse
import csv
import os

import django
from django.db import transaction

django.setup()

from scripts import utils as script_utils

from website.app import init_app
from addons.metadata.utils import ensure_registration_report


logger = logging.getLogger(__name__)


def do_populate(schema_name, report_name, template_file):
    with open(template_file, encoding='utf-8-sig') as f:
        csv_template = f.read()
        ensure_registration_report(schema_name, report_name, csv_template)


def main(schema_name, report_name, template_file, dry=True):
    init_app(routes=False)
    with transaction.atomic():
        do_populate(schema_name, report_name, template_file)
        if dry:
            raise Exception('Abort Transaction - Dry Run')


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dry-run', action='store_true', help='Dry run')
parser.add_argument('schema_name', metavar='schema_name', type=str,
                    help='RegistrationSchema name')
parser.add_argument('report_name', metavar='report_name', type=str,
                    help='RegistrationReportFormat name')
parser.add_argument('template_file', metavar='template_file', type=str,
                    help='Path of the template file for report')

if __name__ == '__main__':
    args = parser.parse_args()
    if not args.dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(args.schema_name, args.report_name, args.template_file, dry=args.dry_run)
