from osf.models import Institution

from .factories import InstitutionFactory
import pytest


@pytest.mark.django_db
def test_factory():
    inst = InstitutionFactory()
    assert isinstance(inst.name, str)
    assert len(inst.domains) > 0
    assert len(inst.email_domains) > 0


@pytest.mark.django_db
def test_querying_on_domains():
    inst = InstitutionFactory(domains=['foo.test'])
    result = Institution.objects.filter(domains__contains=['foo.test'])
    assert inst in result


@pytest.mark.django_db
def test_institution_banner_path_none():
    inst = InstitutionFactory(banner_name='kittens.png')
    assert inst.banner_path is not None
    inst.banner_name = None
    assert inst.banner_path is None


@pytest.mark.django_db
def test_institution_logo_path_none():
    inst = InstitutionFactory(logo_name='kittens.png')
    assert inst.logo_path is not None
    inst.logo_name = None
    assert inst.logo_path is None


@pytest.mark.django_db
def test_institution_logo_path():
    inst = InstitutionFactory(logo_name='osf-shield.png')
    expected_logo_path = '/static/img/institutions/shields/osf-shield.png'
    assert inst.logo_path == expected_logo_path


@pytest.mark.django_db
def test_institution_logo_path_rounded_corners():
    inst = InstitutionFactory(logo_name='osf-shield.png')
    expected_logo_path = '/static/img/institutions/shields-rounded-corners/osf-shield-rounded-corners.png'
    assert inst.logo_path_rounded_corners == expected_logo_path


@pytest.mark.django_db
def test_institution_banner_path():
    inst = InstitutionFactory(banner_name='osf-banner.png')
    expected_banner_path = '/static/img/institutions/banners/osf-banner.png'
    assert inst.banner_path == expected_banner_path
