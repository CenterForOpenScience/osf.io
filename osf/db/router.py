from django.conf import settings
import psycopg2

CACHED_MASTER = None


class PostgreSQLFailoverRouter(object):
    """
    1. CHECK MASTER_SERVER_DSN @ THREAD LOCAL
    2. THERE?, GOTO 9
    3. GET RANDOM_SERVER FROM `settings.DATABASES`
    4. CONNECT TO RANDOM_SERVER
    5. IS MASTER SERVER?
    6. YES? GOTO 8
    7. NO?, `exit()`
    8. STOR MASTER_SERVER_DSN @ THREAD_LOCAL
    9. PROFIT
    Number of servers can be assumed to be > 1 but shouldn't assume 2 max.
    Might be nice to keep track of the servers that have been tried from settings.DATABASES so we don't get into a loop.
    """
    DSNS = dict()

    def __init__(self):
        self._get_dsns()
        global CACHED_MASTER
        if not CACHED_MASTER:
            CACHED_MASTER = self._get_master()

    def _get_master(self):
        for name, dsn in self.DSNS.iteritems():
            conn = self._get_conn(dsn)
            cur = conn.cursor()
            cur.execute('SELECT pg_is_in_recovery();')
            row = cur.fetchone()
            if not row[0]:
                cur.close()
                conn.close()
                return name
            cur.close()
            conn.close()
        return None

    def _get_dsns(self):
        template = '{protocol}://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'
        for name, db in settings.DATABASES.iteritems():
            if 'postgresql' in db['ENGINE']:
                db['protocol'] = 'postgres'
                # db.setdefault('protocol', 'postgres')
            else:
                raise Exception('PostgreSQLFailoverRouter only works with PostgreSQL... ... ...')
            self.DSNS[name] = template.format(**db)

    def _get_conn(self, dsn):
        return psycopg2.connect(dsn)

    def db_for_read(self, model, **hints):
        if not CACHED_MASTER:
            exit()
        return CACHED_MASTER

    def db_for_write(self, model, **hints):
        if not CACHED_MASTER:
            exit()
        return CACHED_MASTER

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return None
