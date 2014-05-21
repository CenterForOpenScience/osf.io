
from .query import RawQuery

class QueryDialect(object):

    pass

class DefaultQueryDialect(QueryDialect, RawQuery):

    pass

class DictQueryDialect(QueryDialect):

    pass

class DunderQueryDialect(QueryDialect):

    pass

# '''
# __Q(foo='bar', baz__startswith='fez')
# __Q(__or(foo='bar', baz__startswith='fez'))
# __Q(__and(__or(foo='bar', baz__startswith='fez'), qux__ne='mom'))
# '''