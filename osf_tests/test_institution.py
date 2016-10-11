from osf.models import Institution

from modularodm import Q

from .factories import InstitutionFactory
import pytest


@pytest.mark.django_db
def test_factory():
    inst = InstitutionFactory()
    assert isinstance(inst.name, basestring)
    assert len(inst.domains) > 0
    assert len(inst.email_domains) > 0


@pytest.mark.django_db
def test_querying_on_domains():
    inst = InstitutionFactory(domains=['foo.test'])
    result = Institution.find(Q('domains', 'eq', 'foo.test'))
    assert inst in result
