
import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Runs VACUUM [ANALYZE] on tables.

    Examples:

        python manage.py vacuum --dry osf.OSFUser
        python manage.py vacuum --analyze osf.OSFUser
        python manage.py vacuum osf.OSFUser osf.Node
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('models', nargs='+', type=str)
        parser.add_argument(
            '--analyze',
            action='store_true',
            dest='analyze',
            help='Whether to run VACUUM ANALYZE'
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry',
            help='If true, no SQL commands will be executed'
        )

    def handle(self, *args, **options):
        analyze = options.get('analyze', False)
        model_names = options.get('models', [])
        dry = options.get('dry', False)
        models = [
            apps.get_model(each)
            for each in model_names
        ]
        table_names = [
            each._meta.db_table
            for each in models
        ]
        statement_format = 'VACUUM ANALYZE {table};' if analyze else 'VACUUM {table};'
        statements = [
            statement_format.format(table=table)
            for table in table_names
        ]
        if dry:
            for statement in statements:
                logger.info('[DRY]: {}'.format(statement))
        else:
            with connection.cursor() as cursor:
                for table in table_names:
                    statement = statement_format.format(table=table)
                    logger.info(statement)
                    cursor.execute(statement)
