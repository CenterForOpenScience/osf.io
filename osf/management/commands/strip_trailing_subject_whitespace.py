# -*- coding: utf-8 -*-
# This is a management command, rather than a migration script, for three primary reasons:
#   1. It makes no changes to database structure (e.g. AlterField), only database content.
#   2. It may need to be ran more than once. (Unlikely, but possible).
#   3. A reverse migration isn't possible without making a back-up table.

from __future__ import unicode_literals
import logging

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Strip trailing whitespace from osf_subject.text
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

    def handle(self, *args, **options):
        sql_select = """
        SELECT id, text
        FROM osf_subject
        WHERE text LIKE '% ';
        """
        sql_update = """
        UPDATE osf_subject
        SET text = TRIM(TRAILING FROM text, ' ')
        WHERE text LIKE '% ';
        """
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(sql_select)
                rows = cursor.fetchall()
                logger.info('Preparing to update {} rows:'.format(len(rows)))
                for row in rows:
                    logger.info('\tSubject {} -- {}'.format(row[0], row[1]))
                cursor.execute(sql_update)
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
