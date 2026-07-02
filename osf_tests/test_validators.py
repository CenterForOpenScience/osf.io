import pytest
from osf.exceptions import ValidationValueError

from osf.models import validators
from osf.models.validators import has_domain_in_user_fields_for_names
from osf_tests.factories import SubjectFactory, AuthUserFactory


# Ported from tests/framework/test_mongo.py

@pytest.fixture()
def user(user_data):
    return AuthUserFactory(**user_data)


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
    'user_data',
    [
        {
            'fullname': 'Judith Sarah Preuss, M.Sc.',
            'given_name': 'Judith',
            'family_name': 'Preuss',
            'middle_names': 'Sarah',
            'suffix': 'M.Sc.',
        },
        {
            'fullname': 'J.H. van Hateren',
            'given_name': 'J.H.',
            'family_name': 'van Hateren',
            'middle_names': '',
        },
        {
            'fullname': 'Sami-Egil Ahonen',
            'given_name': 'Sami-Egil',
            'family_name': 'Ahonen',
            'middle_names': '',
        },
        {
            'fullname': 'Giovanni Luca Ciampaglia',
            'given_name': 'Giovanni Luca',
            'family_name': 'Ciampaglia',
            'middle_names': '',
        },
        {
            'fullname': 'Joseph P.R.O. Orgel',
            'given_name': 'Joseph',
            'family_name': 'Orgel',
            'middle_names': 'P.R.O.',
        },
        {
            'fullname': 'Andrew Daoust',
            'given_name': 'Andrew',
            'family_name': 'Daoust',
            'middle_names': '',
        },
        {
            'fullname': 'Aidan G.C. Wright',
            'given_name': 'Aidan',
            'family_name': 'Wright',
            'middle_names': 'G.C.',
        },
        {
            'fullname': 'Guillermo Perez Algorta',
            'given_name': 'Guillermo',
            'family_name': 'Perez Algorta',
            'middle_names': '',
        },
        {
            'fullname': 'Sarah Wojkowski, MSc.PT, PhD.',
            'given_name': 'Sarah',
            'family_name': 'Wojkowski',
            'middle_names': 'MSc.PT',
        },
        {
            'fullname': 'Brockmann, L.C. (Leon)',
            'given_name': 'Leon',
            'family_name': 'Brockmann',
            'middle_names': 'L.C.',
        },
        {
            'fullname': 'Gragnolati, G.M. (Gaia Mariavittoria)',
            'given_name': 'Gaia',
            'family_name': 'Gragnolati',
            'middle_names': 'G.M.',
        },
        {
            'fullname': 'F.H. Leeuwis',
            'given_name': 'F.H.',
            'family_name': 'Leeuwis',
            'middle_names': '',
        },
        {
            'fullname': 'Grauss, S.E. (Sophie)',
            'given_name': 'Sophie',
            'family_name': 'Grauss',
            'middle_names': 'S.E.',
        },
        {
            'fullname': 'Sandhya N.Sathesh',
            'given_name': 'Sandhya',
            'family_name': 'N.Sathesh',
            'middle_names': '',
        },
        {
            'fullname': 'John Doe',
            'given_name': 'John',
            'family_name': 'Doe',
            'middle_names': '',
        }
    ]
)
def test_has_domain_in_user_fields_for_names_returns_false(user, user_data):
    user.DOMAIN_VALIDATION_FIELDS = [
        'fullname',
        'given_name',
        'middle_names',
        'family_name',
        'suffix',
    ]

    assert has_domain_in_user_fields_for_names(user) is False