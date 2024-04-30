import csv
import pytest

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
class TestInstitutionUsersListCSVRenderer:
    # Existing setup and tests...

    def test_csv_output(self, app, institution, users):
        """
        Test to ensure the CSV renderer returns data in the expected CSV format with correct headers.
        """
        url = reverse(
            'institutions:institution-users-list-dashboard',
            kwargs={
                'version': 'v2',
                'institution_id': institution._id
            }
        ) + '?format=csv'
        response = app.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'

        # Read the content of the response as CSV
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content))
        headers = next(csv_reader)  # First line contains headers

        # Define expected headers based on the serializer used
        expected_headers = ['ID', 'Email', 'Department', 'Public Projects', 'Private Projects', 'Public Registrations',
                            'Private Registrations', 'Preprints']
        assert headers == expected_headers, "CSV headers do not match expected headers"

        # Optionally, check a few lines of actual data if necessary
        for row in csv_reader:
            assert len(row) == len(expected_headers), "Number of data fields in CSV does not match headers"
