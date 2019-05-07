import pytest
from waffle.testutils import override_flag

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf.utils.permissions import MEMBER, MANAGER
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
def old_name():
    return 'Platform Team'

@pytest.fixture()
def osf_group(manager, member, old_name):
    group = OSFGroupFactory(name=old_name, creator=manager)
    group.make_member(member)
    return group

@pytest.fixture()
def url(osf_group, member):
    return '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, member._id)

@pytest.fixture()
def bad_url(osf_group):
    return '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, '12345')

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersDetail:
    def test_return_perms(self, app, member, manager, user, osf_group, url, bad_url):
        with override_flag(OSF_GROUPS, active=True):
            # test unauthenticated
            res = app.get(url)
            assert res.status_code == 200

            # test user
            res = app.get(url, auth=user.auth)
            assert res.status_code == 200

            # test member
            res = app.get(url, auth=member.auth)
            assert res.status_code == 200

            # test manager
            res = app.get(url, auth=manager.auth)
            assert res.status_code == 200

            # test invalid member
            res = app.get(bad_url, auth=manager.auth, expect_errors=True)
            assert res.status_code == 404

    def test_return_member(self, app, member, manager, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            res = app.get(url)
            assert res.status_code == 200
            data = res.json['data']
            assert data['id'] == '{}-{}'.format(osf_group._id, member._id)
            assert data['type'] == 'group-members'
            assert data['attributes']['role'] == MEMBER
            assert data['attributes']['unregistered_member'] is None
            assert data['attributes']['full_name'] == member.fullname
            assert member._id in data['relationships']['users']['links']['related']['href']

            user = osf_group.add_unregistered_member('Crazy 8s', 'eight@cos.io', Auth(manager), MANAGER)
            res = app.get('/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, user._id))
            assert res.status_code == 200
            data = res.json['data']
            assert data['id'] == '{}-{}'.format(osf_group._id, user._id)
            assert data['type'] == 'group-members'
            assert data['attributes']['role'] == MANAGER
            assert data['attributes']['unregistered_member'] == 'Crazy 8s'
            assert data['attributes']['full_name'] == 'Crazy 8s'
            assert res.json['data']['attributes']['full_name'] == 'Crazy 8s'


def build_update_payload(group_id, user_id, role):
    return {
        'data': {
            'id': '{}-{}'.format(group_id, user_id),
            'type': 'group-members',
            'attributes': {
                'role': role
            }
        }
    }

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersUpdate:
    def test_update_role(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            payload = build_update_payload(osf_group._id, member._id, MANAGER)

            # test unauthenticated
            res = app.patch_json_api(url, payload, expect_errors=True)
            assert res.status_code == 401

            # test user
            res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
            assert res.status_code == 403

            # test member
            res = app.patch_json_api(url, payload, auth=member.auth, expect_errors=True)
            assert res.status_code == 403

            # test manager
            res = app.patch_json_api(url, payload, auth=manager.auth)
            assert res.status_code == 200
            assert res.json['data']['attributes']['role'] == MANAGER
            assert res.json['data']['attributes']['full_name'] == member.fullname
            assert res.json['data']['id'] == '{}-{}'.format(osf_group._id, member._id)

            payload = build_update_payload(osf_group._id, member._id, MEMBER)
            res = app.patch_json_api(url, payload, auth=manager.auth)
            assert res.status_code == 200
            assert res.json['data']['attributes']['role'] == MEMBER
            assert res.json['data']['attributes']['full_name'] == member.fullname
            assert res.json['data']['id'] == '{}-{}'.format(osf_group._id, member._id)

    def test_update_errors(self, app, member, manager, user, osf_group, url, bad_url):
        with override_flag(OSF_GROUPS, active=True):
            # id not in payload
            payload = {
                'data': {
                    'type': 'group-members',
                    'attributes': {
                        'role': MEMBER
                    }
                }
            }
            res = app.patch_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'This field may not be null.'

            # test improperly formatted id
            payload = build_update_payload(osf_group._id, member._id, MANAGER)
            payload['data']['id'] = 'abcde'
            res = app.patch_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 409

            # test improper type
            payload = build_update_payload(osf_group._id, member._id, MANAGER)
            payload['data']['type'] = 'bad_type'
            res = app.patch_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 409

            # test invalid role
            payload = build_update_payload(osf_group._id, member._id, 'bad_perm')
            res = app.patch_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'bad_perm is not a valid role; choose manager or member.'

            # test user is not a member
            payload = build_update_payload(osf_group._id, user._id, MEMBER)
            bad_url = '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, user._id)
            res = app.patch_json_api(bad_url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 404
            assert res.json['errors'][0]['detail'] == '{} cannot be found in this OSFGroup'.format(user._id)

            # test cannot downgrade remaining manager
            payload = build_update_payload(osf_group._id, manager._id, MEMBER)
            manager_url = '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, manager._id)
            res = app.patch_json_api(manager_url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'

            # test cannot remove last confirmed manager
            osf_group.add_unregistered_member('Crazy 8s', 'eight@cos.io', Auth(manager), MANAGER)
            assert len(osf_group.managers) == 2
            res = app.patch_json_api(manager_url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersDelete:
    def test_delete_perms(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            # test unauthenticated
            res = app.delete_json_api(url, expect_errors=True)
            assert res.status_code == 401

            # test user
            res = app.delete_json_api(url, auth=user.auth, expect_errors=True)
            assert res.status_code == 403

            # test member
            osf_group.make_member(user)
            user_url = '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, user._id)
            res = app.delete_json_api(user_url, auth=member.auth, expect_errors=True)
            assert res.status_code == 403

            # test manager
            assert osf_group.is_member(member) is True
            assert osf_group.is_manager(member) is False

            res = app.delete_json_api(url, auth=manager.auth)
            assert res.status_code == 204
            assert osf_group.is_member(member) is False
            assert osf_group.is_manager(member) is False

            # test delete manager (not last manager)
            osf_group.make_manager(user)
            assert osf_group.is_member(user) is True
            assert osf_group.is_manager(user) is True
            user_url = '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, user._id)
            res = app.delete_json_api(user_url, auth=user.auth)
            assert res.status_code == 204
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user) is False

    def test_delete_yourself(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            assert osf_group.is_member(member) is True
            assert osf_group.is_manager(member) is False
            res = app.delete_json_api(url, auth=member.auth, expect_errors=True)
            assert res.status_code == 204
            assert osf_group.is_member(member) is False
            assert osf_group.is_manager(member) is False

    def test_delete_errors(self, app, member, manager, user, osf_group, url, bad_url):
        with override_flag(OSF_GROUPS, active=True):
            # test invalid user
            res = app.delete_json_api(bad_url, auth=manager.auth, expect_errors=True)
            assert res.status_code == 404

            # test user does not belong to group
            bad_url = '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, user._id)
            res = app.delete_json_api(bad_url, auth=manager.auth, expect_errors=True)
            assert res.status_code == 404
            assert res.json['errors'][0]['detail'] == '{} cannot be found in this OSFGroup'.format(user._id)

            # test user is last manager
            manager_url = '/{}groups/{}/members/{}/'.format(API_BASE, osf_group._id, manager._id)
            res = app.delete_json_api(manager_url, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'

            # test user is last registered manager
            osf_group.add_unregistered_member('Crazy 8s', 'eight@cos.io', Auth(manager), MANAGER)
            assert len(osf_group.managers) == 2
            res = app.delete_json_api(manager_url, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'
