import pytest
from osf.exceptions import ValidationValueError

from osf.models import validators, NotableDomain
from osf.models.validators import has_domain_in_user_fields_for_names
from osf_tests.factories import SubjectFactory


# Ported from tests/framework/test_mongo.py

def test_string_required_passes_with_string():
    assert validators.string_required('Hi!') is True

def test_string_required_fails_when_empty():
    with pytest.raises(ValidationValueError):
        validators.string_required(None)
    with pytest.raises(ValidationValueError):
        validators.string_required('')

@pytest.mark.django_db
def test_validate_expand_subject_hierarchy():
    fruit = SubjectFactory()
    apple = SubjectFactory(parent=fruit)
    grapes = SubjectFactory(parent=fruit)
    raisins = SubjectFactory(parent=grapes)

    # test send in two flattened hierarchies that share a base
    subject_list = [fruit._id, apple._id, grapes._id]
    expanded = validators.expand_subject_hierarchy(subject_list)
    assert len(expanded) == 3
    assert fruit in expanded
    assert apple in expanded
    assert grapes in expanded

    # test send in third level of a 3-tier hierarchy
    subject_list = [raisins._id]
    expanded = validators.expand_subject_hierarchy(subject_list)
    assert len(expanded) == 3
    assert raisins in expanded
    assert grapes in expanded
    assert fruit in expanded

    # test send in first and third levels
    subject_list = [raisins._id, fruit._id]
    expanded = validators.expand_subject_hierarchy(subject_list)
    assert len(expanded) == 3
    assert raisins in expanded
    assert grapes in expanded
    assert fruit in expanded

    # test invalid hierarchy
    subject_list = [fruit._id, '12345_bad_id']
    with pytest.raises(ValidationValueError):
        validators.expand_subject_hierarchy(subject_list)

@pytest.mark.parametrize(
    'fullname',
    [
        'Judith Sarah Preuss, M.Sc.',
        'J.H. van Hateren',
        'Sami-Egil Ahonen',
        'Giovanni Luca Ciampaglia',
        'Joseph P.R.O. Orgel',
        'Andrew Daoust',
        'Aidan G.C. Wright',
        'Guillermo Perez Algorta',
        'Sarah Wojkowski, MSc.PT, PhD.',
        'Brockmann, L.C. (Leon)',
        'Gragnolati, G.M. (Gaia Mariavittoria)',
        'F.H. Leeuwis',
        'Grauss, S.E. (Sophie)',
        'Sandhya N.Sathesh',
        'John Doe',
    ]
)
def test_has_domain_in_user_fields(fullname):
    assert has_domain_in_user_fields_for_names(fullname) is False

@pytest.mark.parametrize(
    'fullname',
    [
        'Judith Sarah Visit https://www.google.com today',
        'J.H. https://google.com',
        'Judith Sarah www.google.com',
        'Judith Hateren google.com',
    ]
)
def test_has_domain_in_user_fields_fail(fullname):
    assert has_domain_in_user_fields_for_names(fullname) is True

def test_has_notable_domain_in_user_fields():
    NotableDomain.objects.get_or_create(domain='osf.io', note=NotableDomain.Note.IGNORED)
    assert has_domain_in_user_fields_for_names('Judith Sarah osf.io') is False

def test_has_no_notable_domain_in_user_fields():
    NotableDomain.objects.get_or_create(domain='google.com', note=NotableDomain.Note.IGNORED)
    assert has_domain_in_user_fields_for_names('Judith Sarah osf.io') is True
