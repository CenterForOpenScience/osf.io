from modularodm import Q
from django.db.models import Q as DjangoQ
from osf.modm_compat import to_django_query

class TestToDjangoQuery:

    def test_returns_a_django_q(self):
        q = Q('foo', 'eq', 42)
        django_q = to_django_query(q)
        assert type(django_q) is DjangoQ

    def test_handles_or_queries(self):
        q = Q('foo', 'eq', 42) | Q('bar', 'eq', 24)
        django_q = to_django_query(q)
        assert type(django_q) is DjangoQ
        assert django_q.connector == 'OR'
        assert len(django_q.children) == 2
        assert django_q.children == [('foo__exact', 42), ('bar__exact', 24)]

    def test_handles_and_queries(self):
        q = Q('foo', 'eq', 42) & Q('bar', 'eq', 24)
        django_q = to_django_query(q)
        assert type(django_q) is DjangoQ
        assert django_q.connector == 'AND'
        assert len(django_q.children) == 2
        assert django_q.children == [('foo__exact', 42), ('bar__exact', 24)]
