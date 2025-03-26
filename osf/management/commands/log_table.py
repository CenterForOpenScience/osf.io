import logging

from django.core.management.base import BaseCommand, CommandError

from django.db import connection

logger = logging.getLogger(__name__)


GET_TABLES_SQL = '''
SELECT tablename
FROM pg_catalog.pg_tables
WHERE schemaname = 'public';
'''

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS operation_log (
    log_id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    changed_data JSONB,
    user_name TEXT NOT NULL,
    client_ip INET,
    transaction_id BIGINT,
    statement_text TEXT,
    query_start TIMESTAMP WITH TIME ZONE,
    log_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
'''

TRIGGER_FUNCTION_SQL = '''
-- Trigger function to log metadata
CREATE OR REPLACE FUNCTION log_table_changes() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO operation_log (
        table_name,
        operation_type,
        changed_data,
        user_name,
        client_ip,
        transaction_id,
        statement_text,
        query_start
    )
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        CASE TG_OP
            WHEN 'INSERT' THEN row_to_json(NEW)::jsonb
            WHEN 'UPDATE' THEN jsonb_build_object('old', row_to_json(OLD)::jsonb, 'new', row_to_json(NEW)::jsonb)
            WHEN 'DELETE' THEN row_to_json(OLD)::jsonb
        END,
        current_user,
        inet_client_addr(),
        txid_current(),
        current_query(),
        clock_timestamp()
    );
    RETURN NULL;  -- Triggers on AFTER events don't modify the data
END;
$$ LANGUAGE plpgsql;
'''

TRIGGER_SQL = '''
CREATE TRIGGER change_logger
AFTER INSERT OR UPDATE OR DELETE
ON {}
FOR EACH ROW EXECUTE FUNCTION log_table_changes();
'''
DROP_TRIGGER_SQL = 'DROP TRIGGER IF EXISTS change_logger ON {};'

class Command(BaseCommand):
    """Set storage regions for institutions.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-d',
            '--delete',
            action='store_true',
            help='delete trigger from current table'
        )
        parser.add_argument(
            '-t',
            '--table_name',
            type=str,
            required=True,
            help='Select the table to add the trigger to'
        )

    def handle(self, *args, delete, table_name, **options):
        print(options)
        with connection.cursor() as cursor:
            cursor.execute(GET_TABLES_SQL)
            tables = [row[0] for row in cursor.fetchall()]
            if table_name not in tables:
                raise CommandError('Trying to create trigger on non-existing table')
            cursor.execute(CREATE_TABLE_SQL)
            cursor.execute(TRIGGER_FUNCTION_SQL)
            if delete:
                cursor.execute(DROP_TRIGGER_SQL.format(table_name))
                return
            cursor.execute(TRIGGER_SQL.format(table_name))
