import pytest

from django.contrib.auth.models import Group

from api.base.settings.defaults import API_BASE
from osf.models import OSFGroup
from osf_tests.factories import (
    AuthUserFactory,
    OSFGroupFactory,
)

def build_member_relationship_payload(user_ids):
    return {
        'data': [{
            'type': 'users',
            'id': user_id
        } for user_id in user_ids]
    }

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
def old_name():
    return 'Platform Team'

@pytest.fixture()
def new_name():
    return 'My New Lab'

@pytest.fixture()
def osf_group(manager, member, old_name):
    group = OSFGroupFactory(name=old_name, creator=manager)
    group.make_member(member)
    return group

@pytest.fixture()
def url(osf_group):
    return '/{}osf_groups/{}/'.format(API_BASE, osf_group._id)

@pytest.fixture()
def managers_url(url):
    return url + 'managers/'

@pytest.fixture()
def members_url(url):
    return url + 'members/'

@pytest.fixture()
def name_payload(osf_group, new_name):
    return {
        'data': {
            'id': osf_group._id,
            'type': 'osf_groups',
            'attributes': {
                'name': new_name
            }
        }
    }


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupDetail:

    def test_return(self, app, member, manager, user, osf_group, url):
        # test unauthenticated
        res = app.get(url)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == osf_group._id
        assert data['type'] == 'osf_groups'
        assert data['attributes']['name'] == osf_group.name
        assert 'managers' in data['relationships']
        assert 'members' in data['relationships']

        # test authenticated user
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == osf_group._id
        assert data['type'] == 'osf_groups'
        assert data['attributes']['name'] == osf_group.name
        assert 'managers' in data['relationships']
        assert 'members' in data['relationships']

        # test authenticated member
        res = app.get(url, auth=member.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == osf_group._id
        assert data['type'] == 'osf_groups'
        assert data['attributes']['name'] == osf_group.name
        assert 'managers' in data['relationships']
        assert 'members' in data['relationships']

        # test authenticated manager
        res = app.get(url, auth=manager.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == osf_group._id
        assert data['type'] == 'osf_groups'
        assert data['attributes']['name'] == osf_group.name
        assert 'managers' in data['relationships']
        assert 'members' in data['relationships']

        # test invalid group
        url = '/{}osf_groups/{}/'.format(API_BASE, '12345_bad_id')
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupUpdate:
    def test_patch_osf_group_perms(self, app, member, manager, user, osf_group, url, name_payload, new_name):
        # test unauthenticated
        res = app.patch_json_api(url, expect_errors=True)
        assert res.status_code == 401

        # test authenticated_user
        res = app.patch_json_api(url, {}, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        # test authenticated_member
        res = app.patch_json_api(url, {}, auth=member.auth, expect_errors=True)
        assert res.status_code == 403

        # test authenticated_manager
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == new_name

    def test_patch_osf_group_attributes(self, app, manager, osf_group, url, name_payload, old_name, new_name):
        # test_blank_name
        assert osf_group.name == old_name
        name_payload['data']['attributes']['name'] = ''
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'
        osf_group.reload
        assert osf_group.name == old_name

        # test_name_updated
        name_payload['data']['attributes']['name'] = new_name
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == new_name
        osf_group.reload()
        assert osf_group.name == new_name

        # test_invalid_type
        name_payload['data']['type'] = 'bad_type'
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 409

        # test_id_mismatch
        name_payload['data']['type'] = 'osf_groups'
        name_payload['data']['id'] = '12345_bad_id'
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 409

    def test_patch_osf_group_relationships_add_member(self, app, osf_group, manager, member, user, name_payload, url, members_url, managers_url):
        # Test add member - members overwritten
        assert osf_group.has_permission(manager, 'manage') is True
        assert osf_group.has_permission(manager, 'member') is True

        assert osf_group.has_permission(user, 'manage') is False
        assert osf_group.has_permission(user, 'member') is False

        assert osf_group.has_permission(member, 'manage') is False
        assert osf_group.has_permission(member, 'member') is True

        name_payload['data']['relationships'] = {
            'members': build_member_relationship_payload([user._id])
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200
        osf_group.reload()
        assert osf_group.has_permission(manager, 'manage') is True
        assert osf_group.has_permission(manager, 'member') is True

        assert osf_group.has_permission(user, 'manage') is False
        assert osf_group.has_permission(user, 'member') is True

        assert osf_group.has_permission(member, 'manage') is False
        assert osf_group.has_permission(member, 'member') is False
        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        assert manager._id in [man['id'] for man in res.json['data']]

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        assert user._id in [mem['id'] for mem in res.json['data']]

    def test_patch_osf_group_relationships_add_manager(
        self, app, osf_group, manager, member, user, name_payload,
        url, members_url, managers_url
    ):
        name_payload['data']['relationships'] = {
            'managers': build_member_relationship_payload([manager._id, user._id])
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200

        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 2
        manager_ids = [man['id'] for man in res.json['data']]
        assert manager._id in manager_ids
        assert user._id in manager_ids

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        member_ids = [mem['id'] for mem in res.json['data']]
        assert member._id in member_ids

    def test_patch_osf_group_relationships_remove_all_managers(
        self, app, osf_group, manager, member, user, name_payload,
        url, members_url, managers_url
    ):
        name_payload['data']['relationships'] = {
            'managers': {
                'data': []
            }
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'

        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        manager_ids = [man['id'] for man in res.json['data']]
        assert manager._id in manager_ids

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        member_ids = [mem['id'] for mem in res.json['data']]
        assert member._id in member_ids

    def test_patch_osf_group_relationships_remove_all_members(
        self, app, osf_group, manager, member, user, name_payload,
        url, members_url, managers_url
    ):
        name_payload['data']['relationships'] = {
            'members': {
                'data': []
            }
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200

        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        manager_ids = [man['id'] for man in res.json['data']]
        assert manager._id in manager_ids

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 0

    def test_patch_osf_group_relationships_double_specified(
        self, app, osf_group, manager, member, user, name_payload,
        url, members_url, managers_url
    ):
        name_payload['data']['relationships'] = {
            'managers': build_member_relationship_payload([manager._id, user._id]),
            'members': build_member_relationship_payload([user._id]),
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot specify a user as both a member and a manager of an OSF Group.'

    def test_patch_osf_group_relationships_remove_self_as_manager(
        self, app, osf_group, manager, member, user, name_payload,
        url, members_url, managers_url
    ):
        name_payload['data']['relationships'] = {
            'managers': build_member_relationship_payload([user._id]),
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200

        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        manager_ids = [man['id'] for man in res.json['data']]
        assert user._id in manager_ids

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        member_ids = [mem['id'] for mem in res.json['data']]
        assert member._id in member_ids

    def test_patch_osf_group_relationships_user_not_found(
        self, app, osf_group, manager, member, user, name_payload,
        url, members_url, managers_url
    ):
        name_payload['data']['relationships'] = {
            'managers': build_member_relationship_payload(['12345']),
        }
        res = app.patch_json_api(url, name_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'User was not found'

        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        manager_ids = [man['id'] for man in res.json['data']]
        assert manager._id in manager_ids

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        member_ids = [mem['id'] for mem in res.json['data']]
        assert member._id in member_ids

    def test_can_update_relationships_without_attributes(
        self, app, osf_group, manager, member, user,
        url, members_url, managers_url, old_name
    ):
        relationships_payload = {
            'data': {
                'type': 'osf_groups',
                'id': osf_group._id,
                'relationships': {
                    'managers': build_member_relationship_payload([member._id]),
                    'members': build_member_relationship_payload([manager._id, user._id]),
                }
            }
        }

        res = app.patch_json_api(url, relationships_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 200

        res = app.get(managers_url, auth=manager.auth)
        assert len(res.json['data']) == 1
        manager_ids = [man['id'] for man in res.json['data']]
        assert member._id in manager_ids

        res = app.get(members_url, auth=manager.auth)
        assert len(res.json['data']) == 2
        member_ids = [mem['id'] for mem in res.json['data']]
        assert manager._id in member_ids
        assert user._id in member_ids

        osf_group.reload()
        assert osf_group.name == old_name


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupDelete:
    def test_delete_perms(self, app, osf_group, manager, member, user, url):
        res = app.delete_json_api(url, expect_errors=True)
        assert res.status_code == 401

        res = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.delete_json_api(url, auth=member.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.delete_json_api(url, auth=manager.auth)
        assert res.status_code == 204

    def test_delete_specifics(self, app, osf_group, manager, member, user, url):
        osf_group_name = osf_group.name
        manager_group_name = osf_group.manager_group.name
        member_group_name = osf_group.member_group.name

        assert manager_group_name in manager.groups.values_list('name', flat=True)
        assert member_group_name in member.groups.values_list('name', flat=True)

        res = app.delete_json_api(url, auth=manager.auth)
        assert res.status_code == 204

        assert not OSFGroup.objects.filter(name=osf_group_name).exists()
        assert not Group.objects.filter(name=manager_group_name).exists()
        assert not Group.objects.filter(name=member_group_name).exists()

        assert manager_group_name not in manager.groups.values_list('name', flat=True)
        assert member_group_name not in member.groups.values_list('name', flat=True)

        res = app.get(url, auth=manager.auth, expect_errors=True)
        assert res.status_code == 404
