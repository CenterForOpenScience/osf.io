import pytest
from waffle.testutils import override_flag

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    OSFGroupFactory,
)
from osf.features import OSF_GROUPS


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def manager():
    return AuthUserFactory()

@pytest.fixture()
def member():
    return AuthUserFactory()

@pytest.fixture()
def osf_group(manager, member):
    group = OSFGroupFactory(name='Platform Team', creator=manager)
    group.make_member(member)
    return group

@pytest.fixture()
def second_osf_group(manager, member):
    group = OSFGroupFactory(name='Interfaces Team', creator=manager)
    return group


@pytest.mark.django_db
class TestUserGroupList:

    @pytest.fixture()
    def manager_url(self, manager):
        return '/{}users/{}/groups/'.format(API_BASE, manager._id)

    @pytest.fixture()
    def member_url(self, member):
        return '/{}users/{}/groups/'.format(API_BASE, member._id)

    def test_return_manager_groups(self, app, member, manager, user, osf_group, second_osf_group, manager_url):
        with override_flag(OSF_GROUPS, active=True):
            # test nonauthenticated
            res = app.get(manager_url)
            assert res.status_code == 200
            ids = [group['id'] for group in res.json['data']]
            assert len(ids) == 0

            # test authenticated user
            res = app.get(manager_url, auth=user.auth)
            assert res.status_code == 200
            ids = [group['id'] for group in res.json['data']]
            assert len(ids) == 0

            # test authenticated member
            res = app.get(manager_url, auth=member.auth)
            assert res.status_code == 200
            ids = [group['id'] for group in res.json['data']]
            assert len(ids) == 1

            # test authenticated manager
            res = app.get(manager_url, auth=manager.auth)
            assert res.status_code == 200
            ids = [group['id'] for group in res.json['data']]
            assert len(ids) == 2
            assert osf_group._id in ids
            assert second_osf_group._id in ids

    def test_groups_filter(self, app, member, manager, user, osf_group, second_osf_group, manager_url):
        with override_flag(OSF_GROUPS, active=True):
            res = app.get(manager_url + '?filter[name]=Platform', auth=manager.auth)
            assert res.status_code == 200
            data = res.json['data']
            assert len(data) == 1
            assert data[0]['id'] == osf_group._id

            res = app.get(manager_url + '?filter[name]=Apple', auth=manager.auth)
            assert res.status_code == 200
            data = res.json['data']
            assert len(data) == 0

            res = app.get(manager_url + '?filter[bad_field]=Apple', auth=manager.auth, expect_errors=True)
            assert res.status_code == 400

    def test_return_member_groups(self, app, member, manager, user, osf_group, second_osf_group, member_url):
        with override_flag(OSF_GROUPS, active=True):
            # test nonauthenticated
            res = app.get(member_url)
            assert res.status_code == 200
            data = res.json['data']
            assert len(data) == 0

            # test authenticated user
            res = app.get(member_url, auth=user.auth)
            assert res.status_code == 200
            data = res.json['data']
            assert len(data) == 0

            # test authenticated member
            res = app.get(member_url, auth=member.auth)
            assert res.status_code == 200
            data = res.json['data']
            assert len(data) == 1
            assert data[0]['id'] == osf_group._id

            # test authenticated manager
            res = app.get(member_url, auth=manager.auth)
            assert res.status_code == 200
            data = res.json['data']
            assert len(data) == 1
            assert data[0]['id'] == osf_group._id
            assert data[0]['type'] == 'groups'
            assert data[0]['attributes']['name'] == osf_group.name
