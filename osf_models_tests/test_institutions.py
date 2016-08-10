import pytest

from .factories import InstitutionFactory

@pytest.mark.django_db
def test_factory():
    inst = InstitutionFactory()
    assert inst.name
    assert len(inst.email_domains)
    assert len(inst.domains)
