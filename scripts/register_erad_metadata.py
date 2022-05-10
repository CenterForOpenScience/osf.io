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
from addons.metadata.models import ERadRecordSet
from admin.rdm_metadata.erad import ERAD_COLUMNS, validate_record


logger = logging.getLogger(__name__)


def do_populate(file):
    _, filename = os.path.split(file)
    code, _ = os.path.splitext(filename)

    recordset = ERadRecordSet.get_or_create(code=code)

    with open(file, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for record_num, row in enumerate(reader):
            validate_record(record_num, row)
            kenkyusha_no = row['KENKYUSHA_NO']
            kadai_id = row['KADAI_ID']
            nendo = int(row['NENDO'])
            record = recordset.get_or_create_record(kenkyusha_no, kadai_id, nendo)
            for key in ERAD_COLUMNS:
                setattr(record, key.lower(), row[key])
            record.save()
            logger.info(f'Row inserted: {kenkyusha_no}, {kadai_id}')
    recordset.save()


def main(files, dry=True):
    init_app(routes=False)
    with transaction.atomic():
        for file in files:
            do_populate(file)
            if dry:
                raise Exception('Abort Transaction - Dry Run')


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dry-run', action='store_true', help='Dry run')
parser.add_argument('files', metavar='files', type=str, nargs='+',
                    help='Path of the file containing the e-Rad data')

if __name__ == '__main__':
    args = parser.parse_args()
    if not args.dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(args.files, dry=args.dry_run)
