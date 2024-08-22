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
from osf.models import BaseFileNode


@pytest.mark.django_db
class TestInstitutionUsersList:
    """
        These are attrturbutes the users must be sortable for on the institutional dashboard:
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
            'has_orcid'
    """

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def users(self, institution):
        """
        User_one has two public projects and one registrations. User_two has 1 public registrations. User_three has
        1 Public Registristion and 2 Preprints. So 2 public Projects, 3 registrations and 2 Preprints.
        """
        from osf_tests.test_elastic_search import create_file_version

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
        file_ = project.get_addon('osfstorage').get_root().append_file('New Test file.mp3')
        create_file_version(file_, user_one)
        file_.save()

        ProjectFactory(
            creator=user_one,
            is_public=True
        )
        registration = RegistrationFactory(
            creator=user_one,
        )
        file_ = registration.get_addon('osfstorage').get_root().append_file('New Test file 2.5.mp3')
        create_file_version(file_, user_one)
        file_.save()

        RegistrationFactory(
            creator=user_two,
        )

        RegistrationFactory(
            creator=user_three,
        )
        PreprintFactory(
            creator=user_three,
        )
        PreprintFactory(
            creator=user_three,
        )
        project = ProjectFactory(
            creator=user_three,
            is_public=True
        )
        file_ = project.get_addon('osfstorage').get_root().append_file('New Test file 2.mp3')
        create_file_version(file_, user_three)
        file_.save()

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

    @pytest.mark.parametrize('attribute,value,expected_count', [
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

    @pytest.mark.parametrize('attribute', [
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
        assert sorted_values == sorted(sorted_values), 'Values are not sorted correctly'