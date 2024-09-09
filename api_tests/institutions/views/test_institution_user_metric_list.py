import datetime
import csv
from io import StringIO
from random import random
from urllib.parse import urlencode

import pytest
from waffle.testutils import override_flag

from api.base.settings.defaults import API_BASE, DEFAULT_ES_NULL_VALUE
import osf.features
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)

from osf.metrics import UserInstitutionProjectCounts
from osf.metrics.reports import InstitutionalUserReport

@pytest.mark.es
@pytest.mark.django_db
class TestOldInstitutionUserMetricList:

    @pytest.fixture(autouse=True)
    def _waffled(self):
        with override_flag(osf.features.INSTITUTIONAL_DASHBOARD_2024, active=False):
            yield  # these tests apply only before institution dashboard improvements

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
        UserInstitutionProjectCounts(
            user_id=user._id,
            institution_id=institution._id,
            department='Biology dept',
            public_project_count=4,
            private_project_count=4,
            timestamp=datetime.date(2019, 6, 4)
        ).save(refresh=True)

        # New data
        UserInstitutionProjectCounts(
            user_id=user._id,
            institution_id=institution._id,
            department='Biology dept',
            public_project_count=6,
            private_project_count=5,
        ).save()

        UserInstitutionProjectCounts(
            user_id=user2._id,
            institution_id=institution._id,
            department='Psychology dept',
            public_project_count=3,
            private_project_count=2,
        ).save(refresh=True)

    @pytest.fixture()
    def populate_more_counts(self, institution, user, user2, user3, populate_counts):
        # Creates 9 more user records to test pagination with

        users = []
        for i in range(0, 8):
            users.append(AuthUserFactory())

        for test_user in users:
            UserInstitutionProjectCounts(
                user_id=test_user._id,
                institution_id=institution._id,
                department='Psychology dept',
                public_project_count=int(10 * random()),
                private_project_count=int(10 * random()),
            ).save()

        UserInstitutionProjectCounts(
            user_id=user3._id,
            institution_id=institution._id,
            department='Psychology dept',
            public_project_count=int(10 * random()),
            private_project_count=int(10 * random()),
        ).save(refresh=True)

    @pytest.fixture()
    def populate_na_department(self, institution, user4):
        UserInstitutionProjectCounts(
            user_id=user4._id,
            institution_id=institution._id,
            public_project_count=1,
            private_project_count=1,
        ).save(refresh=True)

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

    def test_sort_and_pagination(self, app, url, user, user2, user3, admin, populate_counts, populate_more_counts, institution):
        resp = app.get(f'{url}?sort=user_name&page[size]=1&page=2', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.json['links']['meta']['total'] == 11
        resp = app.get(f'{url}?sort=user_name&page[size]=1&page=11', auth=admin.auth)
        assert resp.json['data'][0]['attributes']['user_name'] == 'Zedd'
        resp = app.get(f'{url}?sort=user_name&page=2', auth=admin.auth)
        assert resp.json['links']['meta']['total'] == 11
        assert resp.json['data'][-1]['attributes']['user_name'] == 'Zedd'

    def test_filter_and_pagination(self, app, user, user2, user3, url, admin, populate_counts, populate_more_counts, institution):
        resp = app.get(f'{url}?page=2', auth=admin.auth)
        assert resp.json['links']['meta']['total'] == 11
        assert resp.json['data'][0]['attributes']['user_name'] == 'Zedd'
        resp = app.get(f'{url}?filter[user_name]=Zedd', auth=admin.auth)
        assert resp.json['links']['meta']['total'] == 1
        assert resp.json['data'][0]['attributes']['user_name'] == 'Zedd'

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


@pytest.mark.django_db
class TestNewInstitutionUserMetricList:
    @pytest.fixture(autouse=True)
    def _waffled(self):
        with override_flag(osf.features.INSTITUTIONAL_DASHBOARD_2024, active=True):
            yield  # these tests apply only after institution dashboard improvements

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def rando(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institutional_admin(self, institution):
        _admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(_admin_user)
        return _admin_user

    @pytest.fixture()
    def unshown_reports(self, institution):
        # unshown because another institution
        _another_institution = InstitutionFactory()
        _report_factory('2024-08', _another_institution, user_id='nother_inst')
        # unshown because old
        _report_factory('2024-07', institution, user_id='old')

    @pytest.fixture()
    def reports(self, institution):
        return [
            _report_factory(
                '2024-08', institution,
                user_id='u_sparse',
                storage_byte_count=53,
            ),
            _report_factory(
                '2024-08', institution,
                user_id='u_orc',
                orcid_id='5555-4444-3333-2222',
                storage_byte_count=8277,
            ),
            _report_factory(
                '2024-08', institution,
                user_id='u_blargl',
                department_name='blargl',
                storage_byte_count=34834834,
            ),
            _report_factory(
                '2024-08', institution,
                user_id='u_orcomma',
                orcid_id='4444-3333-2222-1111',
                department_name='a department, or so, that happens, incidentally, to have commas',
                storage_byte_count=736662999298,
            ),
        ]

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/metrics/users/'

    def test_anon(self, app, url):
        _resp = app.get(url, expect_errors=True)
        assert _resp.status_code == 401

    def test_rando(self, app, url, rando):
        _resp = app.get(url, auth=rando.auth, expect_errors=True)
        assert _resp.status_code == 403

    @pytest.mark.es
    def test_get_empty(self, app, url, institutional_admin):
        _resp = app.get(url, auth=institutional_admin.auth)
        assert _resp.status_code == 200
        assert _resp.json['data'] == []

    @pytest.mark.es
    def test_get_reports(self, app, url, institutional_admin, institution, reports, unshown_reports):
        _resp = app.get(url, auth=institutional_admin.auth)
        assert _resp.status_code == 200
        assert len(_resp.json['data']) == len(reports)
        _expected_user_ids = {_report.user_id for _report in reports}
        assert set(_user_ids(_resp)) == _expected_user_ids

    @pytest.mark.es
    def test_filter_reports(self, app, url, institutional_admin, institution, reports, unshown_reports):
        for _query, _expected_user_ids in (
            ({'filter[department]': 'nunavum'}, set()),
            ({'filter[department]': 'incidentally'}, set()),
            ({'filter[department]': 'blargl'}, {'u_blargl'}),
            ({'filter[department]': 'a department, or so, that happens, incidentally, to have commas'}, {'u_orcomma'}),
            ({'filter[department][eq]': 'nunavum'}, set()),
            ({'filter[department][eq]': 'blargl'}, {'u_blargl'}),
            ({'filter[department][eq]': 'a department, or so, that happens, incidentally, to have commas'}, {'u_orcomma'}),
            ({'filter[department][ne]': 'nunavum'}, {'u_sparse', 'u_blargl', 'u_orc', 'u_orcomma'}),

            ({'filter[orcid_id][eq]': '5555-4444-3333-2222'}, {'u_orc'}),
            ({'filter[orcid_id][ne]': ''}, {'u_orc', 'u_orcomma'}),
            ({'filter[orcid_id][eq]': ''}, {'u_sparse', 'u_blargl'}),
            ({
                'filter[orcid_id]': '',
                'filter[department]': 'blargl',
            }, {'u_blargl'}),
            ({
                'filter[orcid_id]': '',
                'filter[department][ne]': 'blargl',
            }, {'u_sparse'}),
            ({
                'filter[orcid_id]': '5555-4444-3333-2222',
                'filter[department][ne]': 'blargl',
            }, {'u_orc'}),
            ({
                'filter[orcid_id]': '5555-4444-3333-2222',
                'filter[department][ne]': '',
            }, set()),
        ):
            _resp = app.get(f'{url}?{urlencode(_query)}', auth=institutional_admin.auth)
            assert _resp.status_code == 200
            assert set(_user_ids(_resp)) == _expected_user_ids

    @pytest.mark.es
    def test_sort_reports(self, app, url, institutional_admin, institution, reports, unshown_reports):
        for _query, _expected_user_id_list in (
            ({'sort': 'storage_byte_count'}, ['u_sparse', 'u_orc', 'u_blargl', 'u_orcomma']),
            ({'sort': '-storage_byte_count'}, ['u_orcomma', 'u_blargl', 'u_orc', 'u_sparse']),
        ):
            _resp = app.get(f'{url}?{urlencode(_query)}', auth=institutional_admin.auth)
            assert _resp.status_code == 200
            assert list(_user_ids(_resp)) == _expected_user_id_list

    @pytest.mark.es
    def test_paginate_reports(self, app, url, institutional_admin, institution, reports, unshown_reports):
        for _query, _expected_user_id_list in (
            ({'sort': 'storage_byte_count', 'page[size]': 2}, ['u_sparse', 'u_orc']),
            ({'sort': 'storage_byte_count', 'page[size]': 2, 'page': 2}, ['u_blargl', 'u_orcomma']),
            ({'sort': '-storage_byte_count', 'page[size]': 3}, ['u_orcomma', 'u_blargl', 'u_orc']),
            ({'sort': '-storage_byte_count', 'page[size]': 3, 'page': 2}, ['u_sparse']),
        ):
            _resp = app.get(f'{url}?{urlencode(_query)}', auth=institutional_admin.auth)
            assert _resp.status_code == 200
            assert list(_user_ids(_resp)) == _expected_user_id_list

def _user_ids(api_response):
    for _datum in api_response.json['data']:
        yield _datum['relationships']['user']['data']['id']

def _report_factory(yearmonth, institution, **kwargs):
    _report = InstitutionalUserReport(
        report_yearmonth=yearmonth,
        institution_id=institution._id,
        **kwargs,
    )
    _report.save(refresh=True)
    return _report
