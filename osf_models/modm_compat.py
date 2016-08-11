# -*- coding: utf-8 -*-
from operator import and_, or_

from django.db.models import Q as DjangoQ

from modularodm import Q as MODMQ
from modularodm.query import query, QueryGroup


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
        return '<{0}({1})>'.format(
            self.__class__.__name__,
            ', '.join(repr(node) for node in self.nodes)
        )

    @classmethod
    def from_modm_query(cls, query, model_cls=None):
        op_function = and_ if query.operator == 'and' else or_
        return reduce(op_function, (Q.from_modm_query(node, model_cls) for node in query.nodes))

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

    @classmethod
    def from_modm_query(cls, query, model_cls=None):
        if isinstance(query, QueryGroup):
            compound_cls = AndQ if query.operator == 'and' else OrQ
            return compound_cls.from_modm_query(query, model_cls=model_cls)
        elif isinstance(query, MODMQ):
            if model_cls:
                field = _get_field(model_cls, query.attribute)
                # Mongo compatibility fix: an 'eq' query on array fields behaves like 'contains' for postgres ArrayFields
                if field.get_internal_type() == 'ArrayField' and query.operator == 'eq':
                    return cls(query.attribute, 'contains', [query.argument])
            return cls(query.attribute, query.operator, query.argument)
        elif isinstance(query, cls):
            return query
        else:
            raise ValueError(
                'from_modm_query must receive either a modularodm.Q, modularodm.query.QueryGroup, '
                'or osf_models.modm_compat.Q object'
            )

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
        return self.QUERY_MAP.get(self.__op, self.__op)

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

def _get_field(model_cls, field_name):
    # Prevent circular import
    from osf_models.models.base import ObjectIDMixin, GuidMixin
    if issubclass(model_cls, ObjectIDMixin) and field_name == '_id':
        field_name = 'guid'
    elif issubclass(model_cls, GuidMixin) and field_name == '_id':
        field_name = '_guid'
    return model_cls._meta.get_field(field_name)

def to_django_query(query, model_cls=None):
    """Translate a modular-odm Q or QueryGroup to a Django query.
    """
    return Q.from_modm_query(query, model_cls=model_cls).to_django_query()
