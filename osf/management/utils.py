from django.utils.six.moves import input
import sqlparse

def print_sql(sql):
    """Pretty-print a SQL string. Also works with Django Query objects.

    >>> qs = User.objects.all()
    >>> print_sql(qs.query)
    """
    print(sqlparse.format(str(sql), reindent=True))


# From https://stackoverflow.com/a/39257511/1157536
def ask_for_confirmation(question, default=None):
    """Ask for confirmation before proceeding.
    """
    result = input('{} '.format(question))
    if not result and default is not None:
        return default
    while len(result) < 1 or result[0].lower() not in 'yn':
        result = input('Please answer yes or no: ')
    return result[0].lower() == 'y'
