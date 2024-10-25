"""
Register the mapping definition file for WEKO deposit.
"""

import logging
import argparse
import json

import django
from django.db import transaction

django.setup()

from scripts import utils as script_utils

from website.app import init_app
from addons.weko.utils import ensure_registration_metadata_mapping


logger = logging.getLogger(__name__)


def do_populate(schema_name, mapping_file):
    with open(mapping_file) as f:
        mapping = json.load(f)
        ensure_registration_metadata_mapping(
            schema_name, mapping
        )


def main(schema_name, mapping_file, dry=True):
    init_app(routes=False)
    with transaction.atomic():
        do_populate(schema_name, mapping_file)
        if dry:
            raise Exception('Abort Transaction - Dry Run')


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dry-run', action='store_true', help='Dry run')
parser.add_argument('schema_name', metavar='schema_name', type=str,
                    help='RegistrationSchema name')
parser.add_argument('mapping_file', metavar='mapping_file', type=str,
                    help='Path of the mapping file for conversion')

if __name__ == '__main__':
    args = parser.parse_args()
    if not args.dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(args.schema_name, args.mapping_file, dry=args.dry_run)
