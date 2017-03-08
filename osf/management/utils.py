import sqlparse

def print_sql(sql):
    """Pretty-print a SQL string. Also works with Django Query objects.

    >>> qs = User.objects.all()
    >>> print_sql(qs.query)
    """
    print(sqlparse.format(str(sql), reindent=True))
