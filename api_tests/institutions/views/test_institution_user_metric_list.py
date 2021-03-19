import pytest
import datetime
import csv
from io import StringIO
from random import random
import time

from api.base.settings.defaults import API_BASE, DEFAULT_ES_NULL_VALUE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)

from osf.metrics import UserInstitutionProjectCounts
from api.base import settings

@pytest.mark.es
@pytest.mark.django_db
class TestInstitutionUserMetricList:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
        user = AuthUserFactory()
        user.fullname = user.fullname + ',a'
        user.save()
        return user

    @pytest.fixture()
    def user2(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user3(self):
        return AuthUserFactory(fullname='Zedd')

    @pytest.fixture()
    def user4(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self, institution):
        user = AuthUserFactory()
        group = institution.get_group('institutional_admins')
        group.user_set.add(user)
        group.save()
        return user

    @pytest.fixture()
    def populate_counts(self, institution, user, user2):
        # Old data that shouldn't appear in responses
        UserInstitutionProjectCounts.record(
            user_id=user._id,
            institution_id=institution._id,
            department='Biology dept',
            public_project_count=4,
            private_project_count=4,
            timestamp=datetime.date(2019, 6, 4)
        ).save()

        # New data
        UserInstitutionProjectCounts.record(
            user_id=user._id,
            institution_id=institution._id,
            department='Biology dept',
            public_project_count=6,
            private_project_count=5,
        ).save()

        UserInstitutionProjectCounts.record(
            user_id=user2._id,
            institution_id=institution._id,
            department='Psychology dept',
            public_project_count=3,
            private_project_count=2,
        ).save()

        time.sleep(10)

    @pytest.fixture()
    def populate_more_counts(self, institution, user, user2, user3, populate_counts):
        # Creates 9 more user records to test pagination with

        users = []
        for i in range(0, 8):
            users.append(AuthUserFactory())

        for test_user in users:
            UserInstitutionProjectCounts.record(
                user_id=test_user._id,
                institution_id=institution._id,
                department='Psychology dept',
                public_project_count=int(10 * random()),
                private_project_count=int(10 * random()),
            ).save()

        UserInstitutionProjectCounts.record(
            user_id=user3._id,
            institution_id=institution._id,
            department='Psychology dept',
            public_project_count=int(10 * random()),
            private_project_count=int(10 * random()),
        ).save()

        time.sleep(10)

    @pytest.fixture()
    def populate_na_department(self, institution, user4):
        UserInstitutionProjectCounts.record(
            user_id=user4._id,
            institution_id=institution._id,
            public_project_count=1,
            private_project_count=1,
        ).save()

        time.sleep(10)

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/metrics/users/'

    def test_auth(self, app, url, user, admin):

        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(url, auth=admin.auth)
        assert resp.status_code == 200

        assert resp.json['data'] == []

    def test_get(self, app, url, user, user2, admin, institution, populate_counts):
        resp = app.get(url, auth=admin.auth)

        assert resp.json['data'] == [
            {
                'id': user._id,
                'type': 'institution-users',
                'attributes': {
                    'user_name': user.fullname,
                    'public_projects': 6,
                    'private_projects': 5,
                    'department': 'Biology dept'
                },
                'relationships': {
                    'user': {
                        'links': {
                            'related': {
                                'href': f'http://localhost:8000/v2/users/{user._id}/',
                                'meta': {}
                            }
                        },
                        'data': {
                            'id': user._id,
                            'type': 'users'
                        }
                    }
                },
                'links': {
                    'self': f'http://localhost:8000/v2/institutions/{institution._id}/metrics/users/'
                }
            },
            {
                'id': user2._id,
                'type': 'institution-users',
                'attributes': {
                    'user_name': user2.fullname,
                    'public_projects': 3,
                    'private_projects': 2,
                    'department': 'Psychology dept'
                },
                'relationships': {
                    'user': {
                        'links': {
                            'related': {
                                'href': f'http://localhost:8000/v2/users/{user2._id}/',
                                'meta': {}
                            }
                        },
                        'data': {
                            'id': user2._id,
                            'type': 'users'
                        }
                    }
                },
                'links': {
                    'self': f'http://localhost:8000/v2/institutions/{institution._id}/metrics/users/'
                }
            }
        ]

        # Tests CSV Export
        headers = {
            'accept': 'text/csv'
        }
        resp = app.get(url, auth=admin.auth, headers=headers)
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8'

        response_body = resp.text

        expected_response = [['id', 'user_name', 'public_projects', 'private_projects', 'type'],
            [user._id, user.fullname, '6', '5', 'institution-users'],
            [user2._id, user2.fullname, '3', '2', 'institution-users']]

        with StringIO(response_body) as csv_file:
            csvreader = csv.reader(csv_file, delimiter=',')
            for index, row in enumerate(csvreader):
                assert row == expected_response[index]

    def test_filter(self, app, url, admin, populate_counts):
        resp = app.get(f'{url}?filter[department]=Psychology dept', auth=admin.auth)
        assert resp.json['data'][0]['attributes']['department'] == 'Psychology dept'

    @pytest.mark.skipif(settings.TRAVIS_ENV, reason='Non-deterministic fails on travis')
    def test_sort_and_pagination(self, app, url, user, user2, user3, admin, populate_counts, populate_more_counts, institution):
        resp = app.get(f'{url}?sort=user_name&page[size]=1&page=2', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.json['links']['meta']['total'] == 11
        resp = app.get(f'{url}?sort=user_name&page[size]=1&page=11', auth=admin.auth)
        assert resp.json['data'][0]['attributes']['user_name'] == 'Zedd'
        resp = app.get(f'{url}?sort=user_name&page=2', auth=admin.auth)
        assert resp.json['links']['meta']['total'] == 11
        assert resp.json['data'][-1]['attributes']['user_name'] == 'Zedd'

    @pytest.mark.skipif(settings.TRAVIS_ENV, reason='Non-deterministic fails on travis')
    def test_filter_and_pagination(self, app, user, user2, user3, url, admin, populate_counts, populate_more_counts, institution):
        resp = app.get(f'{url}?page=2', auth=admin.auth)
        assert resp.json['links']['meta']['total'] == 11
        assert resp.json['data'][0]['attributes']['user_name'] == 'Zedd'
        resp = app.get(f'{url}?filter[user_name]=Zedd', auth=admin.auth)
        assert resp.json['links']['meta']['total'] == 1
        assert resp.json['data'][0]['attributes']['user_name'] == 'Zedd'

    @pytest.mark.skipif(settings.TRAVIS_ENV, reason='Non-deterministic fails on travis')
    def test_filter_and_sort(self, app, url, user, user2, user3, admin, user4, populate_counts, populate_na_department, institution):
        """
        Testing for bug where sorting and filtering would throw 502.
        :param app:
        :param url:
        :param admin:
        :param populate_more_counts:
        :return:
        """
        resp = app.get(f'{url}?page=1&page[size]=10&filter[department]={DEFAULT_ES_NULL_VALUE}&sort=user_name', auth=admin.auth)
        assert resp.status_code == 200

        data = resp.json['data']
        assert len(data) == 1
        assert resp.json['links']['meta']['total'] == 1
        assert data[0]['id'] == user4._id

        resp = app.get(f'{url}?page=1&page[size]=10&sort=department', auth=admin.auth)
        assert resp.status_code == 200

        data = resp.json['data']
        assert len(data) == 3
        assert resp.json['links']['meta']['total'] == 3
        assert data[0]['attributes']['department'] == 'Biology dept'
        assert data[1]['attributes']['department'] == 'N/A'
        assert data[2]['attributes']['department'] == 'Psychology dept'
