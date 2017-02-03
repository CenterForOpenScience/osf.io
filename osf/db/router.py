from django.conf import settings
import psycopg2


class PostgreSQLFailoverRouter(object):
    """
    A custom database router that loops through the databases defined in django.conf.settings.DATABASES and returns the
    first one that is not read only. If it finds none that are writable it calls exit() in order to convince docker
    to restart the container.
    """
    DSNS = dict()
    CACHED_MASTER = None

    def __init__(self):
        """
        Builds the list of DSNs from django's config and determines the writeable host.
        """
        self._get_dsns()
        if not self.CACHED_MASTER:
            self.CACHED_MASTER = self._get_master()

    def _get_master(self):
        """
        Finds the first database that's writeable and returns the configuration name.
        :return: :str: name of database config or None
        """
        for name, dsn in self.DSNS.iteritems():
            conn = self._get_conn(dsn)
            cur = conn.cursor()
            cur.execute('SHOW transaction_read_only;')  # 'on' for slaves, 'off' for masters
            row = cur.fetchone()
            if row[0] == u'off':
                cur.close()
                conn.close()
                return name
            cur.close()
            conn.close()
        return None

    def _get_dsns(self):
        """
        Builds a list of databases DSNs
        :return: None
        """
        template = '{protocol}://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'
        for name, db in settings.DATABASES.iteritems():
            if 'postgresql' in db['ENGINE']:
                db['protocol'] = 'postgres'
            else:
                raise Exception('PostgreSQLFailoverRouter only works with PostgreSQL... ... ...')
            self.DSNS[name] = template.format(**db)

    def _get_conn(self, dsn):
        """
        Returns a psycopg2 connection for a DSN
        :param dsn: postgres DSN
        :return: psycopg2 connection
        """
        return psycopg2.connect(dsn)

    def db_for_read(self, model, **hints):
        """
        Returns a django database connection name for reading or kills itself
        :param model: django model (disused)
        :param hints: hints to help choosing a database (disused)
        :return:
        """
        if not self.CACHED_MASTER:
            exit()
        return self.CACHED_MASTER

    def db_for_write(self, model, **hints):
        """
        Returns a django database connection name for writing or kills itself
        :param model: django model (disused)
        :param hints: hints to help choosing a database (disused)
        :return:
        """
        if not self.CACHED_MASTER:
            exit()
        return self.CACHED_MASTER

    def allow_relation(self, obj1, obj2, **hints):
        # None if the router has no opinion
        # https://docs.djangoproject.com/en/1.10/topics/db/multi-db/#allow_relation
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # None if the router has no opinion.
        # https://docs.djangoproject.com/en/1.10/topics/db/multi-db/#allow_migrate
        return None
