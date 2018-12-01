import pytest

from api.base.settings.defaults import API_BASE
from osf.models import OSFUser
from osf.utils.permissions import MEMBER, MANAGE, MANAGER
from osf_tests.factories import (
    AuthUserFactory,
    OSFGroupFactory,
)

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
def url(osf_group):
    return '/{}osf_groups/{}/members/'.format(API_BASE, osf_group._id)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersList:
    def test_return_perms(self, app, member, manager, user, osf_group, url):
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

        # test invalid group
        url = '/{}osf_groups/{}/members/'.format(API_BASE, '12345_bad_id')
        res = app.get(url, auth=manager.auth, expect_errors=True)
        assert res.status_code == 404

    def test_return_members(self, app, member, manager, user, osf_group, url):
        res = app.get(url)
        data = res.json['data']
        assert len(data) == 2
        member_ids = [mem['id'] for mem in data]
        assert '{}-{}'.format(osf_group._id, manager._id) in member_ids
        assert '{}-{}'.format(osf_group._id, member._id) in member_ids

def make_create_payload(role, user=None, full_name=None, email=None):
    base_payload = {
        'data': {
            'type': 'group_members',
            'attributes': {
                'role': role
            }
        }
    }
    if user:
        base_payload['data']['relationships'] = {
            'users': {
                'data': {
                    'id': user._id,
                    'type': 'users'
                }
            }
        }
    else:
        if full_name:
            base_payload['data']['attributes']['full_name'] = full_name
        if email:
            base_payload['data']['attributes']['email'] = email

    return base_payload

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersCreate:
    @pytest.fixture()
    def user3(osf_group):
        return AuthUserFactory()

    def test_create_manager(self, app, manager, user3, osf_group, url):
        payload = make_create_payload(MANAGER, user3)
        res = app.post_json_api(url, payload, auth=manager.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['role'] == MANAGER
        assert data['attributes']['unregistered_member'] is None
        assert data['id'] == '{}-{}'.format(osf_group._id, user3._id)
        assert user3._id in data['relationships']['users']['links']['related']['href']
        assert osf_group.has_permission(user3, MANAGE) is True

    def test_create_member(self, app, member, manager, user3, osf_group, url):
        payload = make_create_payload(MEMBER, user3)
        res = app.post_json_api(url, payload, auth=manager.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['role'] == MEMBER
        assert data['attributes']['unregistered_member'] is None
        assert data['id'] == '{}-{}'.format(osf_group._id, user3._id)
        assert user3._id in data['relationships']['users']['links']['related']['href']
        assert osf_group.has_permission(user3, MANAGE) is False
        assert osf_group.has_permission(user3, MEMBER) is True

    def test_add_unregistered_member(self, app, manager, osf_group, url):
        payload = make_create_payload(MEMBER, user=None, full_name='Crazy 8s', email='eight@cos.io')
        res = app.post_json_api(url, payload, auth=manager.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['role'] == MEMBER
        assert data['attributes']['unregistered_member'] == 'Crazy 8s'
        user = OSFUser.load(data['id'].split('-')[1])
        assert user._id in data['relationships']['users']['links']['related']['href']
        assert osf_group.has_permission(user, MANAGE) is False
        # unregistered members have no perms until account is claimed
        assert osf_group.has_permission(user, MEMBER) is False
        assert user in osf_group.members_only
        assert user not in osf_group.managers

    def test_create_member_perms(self, app, manager, member, osf_group, user3, url):
        payload = make_create_payload(MEMBER, user3)
        # Unauthenticated
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, nonmember
        res = app.post_json_api(url, payload, auth=user3.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in, nonmanager
        res = app.post_json_api(url, payload, auth=member.auth, expect_errors=True)
        assert res.status_code == 403

    def test_create_members_errors(self, app, manager, member, user3, osf_group, url):
        # invalid user
        bad_user_payload = make_create_payload(MEMBER, user=user3)
        bad_user_payload['data']['relationships']['users']['data']['id'] = 'bad_user_id'
        res = app.post_json_api(url, bad_user_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'User with id bad_user_id not found.'

        # invalid type
        bad_type_payload = make_create_payload(MEMBER, user=user3)
        bad_type_payload['data']['type'] = 'bad_type'
        res = app.post_json_api(url, bad_type_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 409

        # invalid role
        bad_perm_payload = make_create_payload('bad_role', user=user3)
        res = app.post_json_api(url, bad_perm_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'bad_role is not a valid role; choose manager or member.'

        # fullname not included
        unregistered_payload = make_create_payload(MEMBER, user=None, full_name=None, email='eight@cos.io')
        res = app.post_json_api(url, unregistered_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You must provide a full_name/email combination to add an unconfirmed member.'

        # email not included
        unregistered_payload = make_create_payload(MEMBER, user=None, full_name='Crazy 8s', email=None)
        res = app.post_json_api(url, unregistered_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You must provide a full_name/email combination to add an unconfirmed member.'

        # user is already a member
        existing_member_payload = make_create_payload(MEMBER, user=member)
        res = app.post_json_api(url, existing_member_payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User is already a member of this group.'

        # No role specified - given member by default
        payload = make_create_payload(MEMBER, user=user3)
        payload['attributes'] = {}
        res = app.post_json_api(url, payload, auth=manager.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['role'] == MEMBER
        assert osf_group.has_permission(user3, 'member')
        assert not osf_group.has_permission(user3, 'manager')
