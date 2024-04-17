import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory
)
from django.shortcuts import reverse


@pytest.mark.django_db
class TestInstitutionUsersList:
    """
        'name',
        '_id',
        'email',
        'department',
        'number_of_public_projects',
        'number_of_private_projects',
        'number_of_public_registrations',
        'number_of_private_registrations',
        'number_of_preprints',
        'number_of_files',
        'last_login',
        'last_log',
        'account_created_date',
        'has_orcid',
    """

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def users(self, institution):
        # Create users with varied attributes
        user_one = AuthUserFactory(
            fullname='Alice Example',
            username='alice@example.com'
        )
        user_two = AuthUserFactory(
            fullname='Bob Example',
            username='bob@example.com'
        )
        user_three = AuthUserFactory(
            fullname='Carol Example',
            username='carol@example.com'
        )
        user_one.add_or_update_affiliated_institution(
            institution,
            sso_department="Science Department"
        )
        user_two.add_or_update_affiliated_institution(institution)
        user_three.add_or_update_affiliated_institution(institution)

        project = ProjectFactory(
            creator=user_one,
            is_public=True
        )
        project2 = ProjectFactory(
            creator=user_one,
            is_public=True
        )
        registration = RegistrationFactory(
            creator=user_one,
        )
        registration = RegistrationFactory(
            creator=user_two,
        )
        registration = RegistrationFactory(
            creator=user_three,
        )
        preprint = PreprintFactory(
            creator=user_three,
        )
        preprint = PreprintFactory(
            creator=user_three,
        )

        return [user_one, user_two, user_three]

    def test_return_all_users(self, app, institution, users):
        url = reverse(
            'institutions:institution-users-list-dashboard',
            kwargs={
                'version': 'v2',
                'institution_id': institution._id
            }
        )
        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == 3

    @pytest.mark.parametrize("attribute,value,expected_count", [
        ('[full_name]', 'Alice Example', 1),
        ('[full_name]', 'Example', 3),  # Multiple users should be returned here
        ('[email_address]', 'bob@example.com', 1),
        ('[department]', 'Science Department', 1),
        ('[number_of_public_projects][lte]', '1', 2),
        ('[number_of_private_projects][lt]', '1', 3),
        ('[number_of_private_projects][gte]', '1', 3),
        ('[number_of_public_registrations][lte]', '1', 1),
        ('[number_of_private_registrations][lte]', '1', 3),
        ('[number_of_preprints][lte]', '2', 1),
        ('[number_of_files][lte]', '1', 0),
        ('[last_login][lte]', '2-11-2018', 0),
        ('[last_log]', 'account_created', 0),
        ('[account_created_date]', '2-11-2018', 0),
        ('[has_orcid]', 'True', 0),
    ])
    def test_filter_users(self, app, institution, users, attribute, value, expected_count):
        url = reverse(
            'institutions:institution-users-list-dashboard',
            kwargs={
                'version': 'v2',
                'institution_id': institution._id
            }
        ) + f'?filter{attribute}={value}'

        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == expected_count

    @pytest.mark.parametrize("attribute", [
        'full_name',
        'email_address',
    ])
    def test_sort_users(self, app, institution, users, attribute):
        url = reverse(
            'institutions:institution-users-list-dashboard',
            kwargs={
                'version': 'v2',
                'institution_id': institution._id
            }
        ) + f'?sort={attribute}'
        res = app.get(url)
        assert res.status_code == 200
        # Extracting sorted attribute values from response
        sorted_values = [user['attributes'][attribute] for user in res.json['data']]
        assert sorted_values == sorted(sorted_values), "Values are not sorted correctly"


@pytest.mark.django_db
class TestInstitutionProjectList:

    def test_return(self, app):

        things_to_filter_and_sort = [
            '_id',
            'title',
            'type',
            'date_modified',
            'date_created',
            'storage_location',
            'storage_usage',
            'is_public',
            'doi',
            'addon_used',
        ]

        res = app.get(f'/{API_BASE}institutions/{institution._id}/users/')

        assert res.status_code == 200


@pytest.mark.django_db
class TestInstitutionRegistrationList:

    def test_return(self, app):

        things_to_filter_and_sort = [
            '_id',
            'title',
            'type',
            'date_modified',
            'date_created',
            'storage_location',
            'storage_usage',
            'is_public',
            'doi',
            'addon_used',
        ]

        res = app.get(f'/{API_BASE}institutions/{institution._id}/users/')

        assert res.status_code == 200


@pytest.mark.django_db
class TestInstitutionPreprintList:

    def test_return(self, app):

        things_to_filter_and_sort = [
            '_id',
            'title',
            'type',
            'date_modified',
            'date_created',
            'storage_location',
            'storage_usage',
            'is_public',
            'doi',
            'addon_used',
        ]

        res = app.get(f'/{API_BASE}institutions/{institution._id}/users/')

        assert res.status_code == 200


@pytest.mark.django_db
class TestInstitutionFilesList:

    def test_return(self, app):

        things_to_filter_and_sort = [
            '_id',
            'file_name',
            'file_path',
            'date_modified',
            'date_created',
            'mime_type',
            'size',
            'resource_type',
            'doi',
            'addon_used',
        ]

        res = app.get(f'/{API_BASE}institutions/{institution._id}/users/')

        assert res.status_code == 200
