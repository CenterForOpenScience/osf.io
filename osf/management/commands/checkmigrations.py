"""
Return a non-zero exit code if there are unapplied migrations.
"""
import sys

from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.executor import MigrationExecutor
from django.core.management.base import BaseCommand

class Command(BaseCommand):

    def handle(self, *args, **options):
        connection = connections[DEFAULT_DB_ALIAS]
        connection.prepare_database()
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        unapplied_migrations = executor.migration_plan(targets)
        if unapplied_migrations:
            self.stdout.write('The following migrations are unapplied:', self.style.ERROR)
            for migration in unapplied_migrations:
                self.stdout.write('  {}.{}'.format(migration[0].app_label, migration[0].name), self.style.MIGRATE_LABEL)
            sys.exit(1)
        self.stdout.write('All migrations have been applied. Have a nice day!', self.style.SUCCESS)
