import sys
from django.db.models import Q as DjangoQ
# from website import settings


# if settings.USE_POSTGRES:
sys.path.pop(0)
sys.modules['__' + __name__] = sys.modules[__name__]
del sys.modules[__name__]
import modularodm
from modularodm.query import query
sys.path[:0] = ['']


class BaseQ(object):

    def __or__(self, other):
        return OrQ(self, other)

    def __and__(self, other):
        return AndQ(self, other)

class CompoundQ(BaseQ, query.QueryGroup):

    @property
    def nodes(self):
        return self.__queries

    def __init__(self, *queries):
        self.__queries = queries

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self.nodes)

class AndQ(CompoundQ):

    operator = 'and'

    def __and__(self, other):
        return AndQ(other, *self.nodes)

    def to_django_query(self):
        return reduce(lambda acc, val: acc & val, (q.to_django_query() for q in self.nodes))

class OrQ(CompoundQ):

    operator = 'or'

    def __or__(self, other):
        return OrQ(other, *self.nodes)

    def to_django_query(self):
        return reduce(lambda acc, val: acc | val, (q.to_django_query() for q in self.nodes))

class Q(BaseQ, query.RawQuery):
    QUERY_MAP = {'eq': 'exact'}

    @property
    def operator(self):
        return self.__op

    @property
    def attribute(self):
        return self.__key

    @property
    def argument(self):
        return self.__val

    @property
    def op(self):
        if self.__val is None:
            return 'isnull'
        return Q.QUERY_MAP.get(self.__op, self.__op)

    @property
    def key(self):
        if self.__key == '_id':
            return 'pk'
        return self.__key

    @property
    def val(self):
        if self.__val is None:
            return True if self.__op == 'eq' else False
        return self.__val

    def __init__(self, key, op, val):
        self.__op = op
        self.__key = key
        self.__val = val

    def to_django_query(self):
        if self.op == 'ne':
            return ~DjangoQ(**{'__'.join(self.key.split('.')): self.val})
        return DjangoQ(**{'__'.join(self.key.split('.') + [self.op]): self.val})

    def __repr__(self):
        return '<Q({}, {}, {})>'.format(self.key, self.op, self.val)

# if settings.USE_POSTGRES:
modularodm.Q = Q
