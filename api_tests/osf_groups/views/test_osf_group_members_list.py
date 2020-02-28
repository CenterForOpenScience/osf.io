import pytest
from waffle.testutils import override_flag

from django.utils import timezone

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf.models import OSFUser
from osf.utils.permissions import MEMBER, MANAGE, MANAGER
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
def user3(osf_group):
    return AuthUserFactory()

@pytest.fixture()
def osf_group(manager, member, old_name):
    group = OSFGroupFactory(name=old_name, creator=manager)
    group.make_member(member)
    return group

@pytest.fixture()
def url(osf_group):
    return '/{}groups/{}/members/'.format(API_BASE, osf_group._id)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestGroupMembersList:
    def test_return_perms(self, app, member, manager, user, osf_group, url):
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

            # test invalid group
            url = '/{}groups/{}/members/'.format(API_BASE, '12345_bad_id')
            res = app.get(url, auth=manager.auth, expect_errors=True)
            assert res.status_code == 404

    def test_return_members(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            res = app.get(url)
            data = res.json['data']
            assert len(data) == 2
            member_ids = [mem['id'] for mem in data]
            assert '{}-{}'.format(osf_group._id, manager._id) in member_ids
            assert '{}-{}'.format(osf_group._id, member._id) in member_ids


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersFilter:
    def test_filtering(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            # test filter members
            url_filter = url + '?filter[role]=member'
            res = app.get(url_filter)
            data = res.json['data']
            assert len(data) == 1
            member_ids = [mem['id'] for mem in data]
            assert '{}-{}'.format(osf_group._id, member._id) in member_ids

            # test filter managers
            url_filter = url + '?filter[role]=manager'
            res = app.get(url_filter)
            data = res.json['data']
            assert len(data) == 1
            member_ids = [mem['id'] for mem in data]
            assert '{}-{}'.format(osf_group._id, manager._id) in member_ids

            # test invalid role
            url_filter = url + '?filter[role]=bad_role'
            res = app.get(url_filter, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == "Value \'bad_role\' is not valid."

            # test filter fullname
            url_filter = url + '?filter[full_name]={}'.format(manager.fullname)
            res = app.get(url_filter)
            data = res.json['data']
            assert len(data) == 1
            member_ids = [mem['id'] for mem in data]
            assert '{}-{}'.format(osf_group._id, manager._id) in member_ids

            # test filter fullname
            url_filter = url + '?filter[full_name]={}'.format(member.fullname)
            res = app.get(url_filter)
            data = res.json['data']
            assert len(data) == 1
            member_ids = [mem['id'] for mem in data]
            assert '{}-{}'.format(osf_group._id, member._id) in member_ids

            # test invalid filter
            url_filter = url + '?filter[created]=2018-02-01'
            res = app.get(url_filter, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == "\'created\' is not a valid field for this endpoint."

def make_create_payload(role, user=None, full_name=None, email=None):
    base_payload = {
        'data': {
            'type': 'group-members',
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
    def test_create_manager(self, app, manager, user3, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            payload = make_create_payload(MANAGER, user3)
            res = app.post_json_api(url, payload, auth=manager.auth)
            assert res.status_code == 201
            data = res.json['data']
            assert data['attributes']['role'] == MANAGER
            assert data['attributes']['full_name'] == user3.fullname
            assert data['attributes']['unregistered_member'] is None
            assert data['id'] == '{}-{}'.format(osf_group._id, user3._id)
            assert user3._id in data['relationships']['users']['links']['related']['href']
            assert osf_group.has_permission(user3, MANAGE) is True

    def test_create_member(self, app, member, manager, user3, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            payload = make_create_payload(MEMBER, user3)
            res = app.post_json_api(url, payload, auth=manager.auth)
            assert res.status_code == 201
            data = res.json['data']
            assert data['attributes']['role'] == MEMBER
            assert data['attributes']['full_name'] == user3.fullname
            assert data['attributes']['unregistered_member'] is None
            assert data['id'] == '{}-{}'.format(osf_group._id, user3._id)
            assert data['id'] == '{}-{}'.format(osf_group._id, user3._id)
            assert user3._id in data['relationships']['users']['links']['related']['href']
            assert osf_group.has_permission(user3, MANAGE) is False
            assert osf_group.has_permission(user3, MEMBER) is True

    def test_add_unregistered_member(self, app, manager, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            full_name = 'Crazy 8s'
            payload = make_create_payload(MEMBER, user=None, full_name=full_name, email='eight@cos.io')
            res = app.post_json_api(url, payload, auth=manager.auth)
            assert res.status_code == 201
            data = res.json['data']
            assert data['attributes']['role'] == MEMBER
            user = OSFUser.load(data['id'].split('-')[1])
            assert user._id in data['relationships']['users']['links']['related']['href']
            assert osf_group.has_permission(user, MANAGE) is False
            assert data['attributes']['full_name'] == full_name
            assert data['attributes']['unregistered_member'] == full_name
            assert osf_group.has_permission(user, MEMBER) is True
            assert user in osf_group.members_only
            assert user not in osf_group.managers

            # test unregistered user is already a member
            res = app.post_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'User already exists.'

            # test unregistered user email is blacklisted
            payload['data']['attributes']['email'] = 'eight@example.com'
            res = app.post_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Email address domain is blacklisted.'

    def test_create_member_perms(self, app, manager, member, osf_group, user3, url):
        with override_flag(OSF_GROUPS, active=True):
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
        with override_flag(OSF_GROUPS, active=True):
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

            # Disabled user
            user3.date_disabled = timezone.now()
            user3.save()
            payload = make_create_payload(MEMBER, user=user3)
            res = app.post_json_api(url, payload, auth=manager.auth, expect_errors=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Deactivated users cannot be added to OSF Groups.'

            # No role specified - given member by default
            user3.date_disabled = None
            user3.save()
            payload = make_create_payload(MEMBER, user=user3)
            payload['attributes'] = {}
            res = app.post_json_api(url, payload, auth=manager.auth)
            assert res.status_code == 201
            assert res.json['data']['attributes']['role'] == MEMBER
            assert osf_group.has_permission(user3, 'member')
            assert not osf_group.has_permission(user3, 'manager')

def make_bulk_create_payload(role, user=None, full_name=None, email=None):
    base_payload = {
        'type': 'group-members',
        'attributes': {
            'role': role
        }
    }

    if user:
        base_payload['relationships'] = {
            'users': {
                'data': {
                    'id': user._id,
                    'type': 'users'
                }
            }
        }
    else:
        if full_name:
            base_payload['attributes']['full_name'] = full_name
        if email:
            base_payload['attributes']['email'] = email

    return base_payload

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersBulkCreate:
    def test_bulk_create_group_member_perms(self, app, url, manager, member, user, user3, osf_group):
        with override_flag(OSF_GROUPS, active=True):
            payload_user_three = make_bulk_create_payload(MANAGER, user3)
            payload_user = make_bulk_create_payload(MEMBER, user)
            bulk_payload = [payload_user_three, payload_user]

            # unauthenticated
            res = app.post_json_api(url, {'data': bulk_payload}, expect_errors=True, bulk=True)
            assert res.status_code == 401

            # non member
            res = app.post_json_api(url, {'data': bulk_payload}, auth=user.auth, expect_errors=True, bulk=True)
            assert res.status_code == 403

            # member
            res = app.post_json_api(url, {'data': bulk_payload}, auth=member.auth, expect_errors=True, bulk=True)
            assert res.status_code == 403

            # manager
            res = app.post_json_api(url, {'data': bulk_payload}, auth=manager.auth, bulk=True)
            assert res.status_code == 201
            assert len(res.json['data']) == 2

            assert osf_group.is_member(user) is True
            assert osf_group.is_member(user3) is True
            assert osf_group.is_manager(user) is False
            assert osf_group.is_manager(user3) is True

    def test_bulk_create_unregistered(self, app, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            payload_user = make_bulk_create_payload(MEMBER, user)
            payload_unregistered = make_bulk_create_payload(MEMBER, user=None, full_name='Crazy 8s', email='eight@cos.io')
            res = app.post_json_api(url, {'data': [payload_user, payload_unregistered]}, auth=manager.auth, bulk=True)
            unreg_user = OSFUser.objects.get(username='eight@cos.io')
            assert res.status_code == 201
            ids = [user_data['id'] for user_data in res.json['data']]
            roles = [user_data['attributes']['role'] for user_data in res.json['data']]
            assert '{}-{}'.format(osf_group._id, user._id) in ids
            assert '{}-{}'.format(osf_group._id, unreg_user._id) in ids
            assert roles[0] == MEMBER
            assert roles[1] == MEMBER
            unregistered_names = [user_data['attributes']['unregistered_member'] for user_data in res.json['data']]
            assert set(['Crazy 8s', None]) == set(unregistered_names)

            assert osf_group.has_permission(user, MANAGE) is False
            assert osf_group.has_permission(user, MEMBER) is True
            assert osf_group.has_permission(unreg_user, MANAGE) is False
            assert osf_group.has_permission(unreg_user, MEMBER) is True
            assert osf_group.is_member(unreg_user) is True
            assert osf_group.is_manager(unreg_user) is False

    def test_bulk_create_group_member_errors(self, app, url, manager, member, user, user3, osf_group):
        with override_flag(OSF_GROUPS, active=True):
            payload_member = make_bulk_create_payload(MANAGER, member)
            payload_user = make_bulk_create_payload(MANAGER, user)

            # User in bulk payload is an invalid user
            bad_user_payload = make_bulk_create_payload(MEMBER, user=user3)
            bad_user_payload['relationships']['users']['data']['id'] = 'bad_user_id'
            bulk_payload = [payload_user, bad_user_payload]
            res = app.post_json_api(url, {'data': bulk_payload}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 404
            assert res.json['errors'][0]['detail'] == 'User with id bad_user_id not found.'
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user) is False

            # User in bulk payload is invalid
            bad_type_payload = make_bulk_create_payload(MEMBER, user=user3)
            bad_type_payload['type'] = 'bad_type'
            bulk_payload = [payload_user, bad_type_payload]
            res = app.post_json_api(url, {'data': bulk_payload}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 409
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user) is False

            # User in bulk payload has invalid role specified
            bad_role_payload = make_bulk_create_payload('bad_role', user=user3)
            res = app.post_json_api(url, {'data': [payload_user, bad_role_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'bad_role is not a valid role; choose manager or member.'
            assert osf_group.is_member(user3) is False
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user3) is False
            assert osf_group.is_manager(user) is False

            # fullname not included
            unregistered_payload = make_bulk_create_payload(MEMBER, user=None, full_name=None, email='eight@cos.io')
            res = app.post_json_api(url, {'data': [payload_user, unregistered_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'You must provide a full_name/email combination to add an unconfirmed member.'
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user) is False

            # email not included
            unregistered_payload = make_bulk_create_payload(MEMBER, user=None, full_name='Crazy 8s', email=None)
            res = app.post_json_api(url, {'data': [payload_user, unregistered_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'You must provide a full_name/email combination to add an unconfirmed member.'
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user) is False

            # Member of bulk payload is already a member
            bulk_payload = [payload_member, payload_user]
            res = app.post_json_api(url, {'data': bulk_payload}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'User is already a member of this group.'
            assert osf_group.is_member(member) is True
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(member) is False
            assert osf_group.is_manager(user) is False

            # Disabled user
            user3.date_disabled = timezone.now()
            user3.save()
            payload = make_bulk_create_payload(MEMBER, user=user3)
            res = app.post_json_api(url, {'data': [payload_user, payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Deactivated users cannot be added to OSF Groups.'

            # No role specified, given member by default
            user3.date_disabled = None
            user3.save()
            payload = make_bulk_create_payload(MEMBER, user=user3)
            payload['attributes'] = {}
            res = app.post_json_api(url, {'data': [payload_user, payload]}, auth=manager.auth, bulk=True)
            assert res.status_code == 201
            assert len(res.json['data']) == 2
            ids = [user_data['id'] for user_data in res.json['data']]
            assert '{}-{}'.format(osf_group._id, user._id) in ids
            assert '{}-{}'.format(osf_group._id, user3._id) in ids
            assert osf_group.is_member(user3) is True
            assert osf_group.is_member(user) is True
            assert osf_group.is_manager(user3) is False
            assert osf_group.is_manager(user) is True

def build_bulk_update_payload(group_id, user_id, role):
    return {
        'id': '{}-{}'.format(group_id, user_id),
        'type': 'group-members',
        'attributes': {
            'role': role
        }
    }


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersBulkUpdate:
    def test_update_role(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            payload = build_bulk_update_payload(osf_group._id, member._id, MANAGER)
            bulk_payload = {'data': [payload]}

            # test unauthenticated
            res = app.patch_json_api(url, bulk_payload, expect_errors=True, bulk=True)
            assert res.status_code == 401

            # test user
            res = app.patch_json_api(url, bulk_payload, auth=user.auth, expect_errors=True, bulk=True)
            assert res.status_code == 403

            # test member
            res = app.patch_json_api(url, bulk_payload, auth=member.auth, expect_errors=True, bulk=True)
            assert res.status_code == 403

            # test manager
            res = app.patch_json_api(url, bulk_payload, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 200
            assert res.json['data'][0]['attributes']['role'] == MANAGER
            assert res.json['data'][0]['attributes']['full_name'] == member.fullname
            assert res.json['data'][0]['id'] == '{}-{}'.format(osf_group._id, member._id)

            payload = build_bulk_update_payload(osf_group._id, member._id, MEMBER)
            bulk_payload = {'data': [payload]}
            res = app.patch_json_api(url, bulk_payload, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 200
            assert res.json['data'][0]['attributes']['role'] == MEMBER
            assert res.json['data'][0]['attributes']['full_name'] == member.fullname
            assert res.json['data'][0]['id'] == '{}-{}'.format(osf_group._id, member._id)

    def test_bulk_update_errors(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            # id not in payload
            payload = {
                'type': 'group-members',
                'attributes': {
                    'role': MEMBER
                }
            }
            bulk_payload = {'data': [payload]}

            res = app.patch_json_api(url, bulk_payload, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Member identifier not provided.'

            # test improperly formatted id
            payload = build_bulk_update_payload(osf_group._id, member._id, MANAGER)
            payload['id'] = 'abcde'
            res = app.patch_json_api(url, {'data': [payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Member identifier incorrectly formatted.'

            # test improper type
            payload = build_bulk_update_payload(osf_group._id, member._id, MANAGER)
            payload['type'] = 'bad_type'
            res = app.patch_json_api(url, {'data': [payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 409

            # test invalid role
            payload = build_bulk_update_payload(osf_group._id, member._id, 'bad_perm')
            res = app.patch_json_api(url, {'data': [payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'bad_perm is not a valid role; choose manager or member.'

            # test user is not a member
            payload = build_bulk_update_payload(osf_group._id, user._id, MEMBER)
            res = app.patch_json_api(url, {'data': [payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

            # test cannot downgrade remaining manager
            payload = build_bulk_update_payload(osf_group._id, manager._id, MEMBER)
            res = app.patch_json_api(url, {'data': [payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'

            # test cannot remove last confirmed manager
            osf_group.add_unregistered_member('Crazy 8s', 'eight@cos.io', Auth(manager), MANAGER)
            assert len(osf_group.managers) == 2
            res = app.patch_json_api(url, {'data': [payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'

def create_bulk_delete_payload(group_id, user_id):
    return {
        'id': '{}-{}'.format(group_id, user_id),
        'type': 'group-members'
    }

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupMembersBulkDelete:
    def test_delete_perms(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            member_payload = create_bulk_delete_payload(osf_group._id, member._id)
            bulk_payload = {'data': [member_payload]}
            # test unauthenticated
            res = app.delete_json_api(url, bulk_payload, expect_errors=True, bulk=True)
            assert res.status_code == 401

            # test user
            res = app.delete_json_api(url, bulk_payload, auth=user.auth, expect_errors=True, bulk=True)
            assert res.status_code == 403

            # test member
            res = app.delete_json_api(url, bulk_payload, auth=member.auth, expect_errors=True, bulk=True)
            assert res.status_code == 403

            # test manager
            assert osf_group.is_member(member) is True
            assert osf_group.is_manager(member) is False

            res = app.delete_json_api(url, bulk_payload, auth=manager.auth, bulk=True)
            assert res.status_code == 204
            assert osf_group.is_member(member) is False
            assert osf_group.is_manager(member) is False

            # test user does not belong to OSF Group
            osf_group.make_manager(user)
            assert osf_group.is_member(user) is True
            assert osf_group.is_manager(user) is True
            user_payload = create_bulk_delete_payload(osf_group._id, user._id)
            bulk_payload = {'data': [user_payload, member_payload]}
            res = app.delete_json_api(url, bulk_payload, auth=user.auth, bulk=True, expect_errors=True)
            assert res.status_code == 404
            assert res.json['errors'][0]['detail'] == '{} cannot be found in this OSFGroup'.format(member._id)

            # test bulk delete manager (not last one)
            osf_group.make_manager(user)
            assert osf_group.is_member(user) is True
            assert osf_group.is_manager(user) is True
            user_payload = create_bulk_delete_payload(osf_group._id, user._id)
            bulk_payload = {'data': [user_payload]}
            res = app.delete_json_api(url, bulk_payload, auth=user.auth, bulk=True)
            assert res.status_code == 204
            assert osf_group.is_member(user) is False
            assert osf_group.is_manager(user) is False

    def test_delete_errors(self, app, member, manager, user, osf_group, url):
        with override_flag(OSF_GROUPS, active=True):
            # test invalid user
            invalid_payload = create_bulk_delete_payload(osf_group._id, '12345')
            res = app.delete_json_api(url, {'data': [invalid_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Could not find all objects to delete.'

            # test user does not belong to group
            invalid_payload = create_bulk_delete_payload(osf_group._id, user._id)
            res = app.delete_json_api(url, {'data': [invalid_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 404
            assert res.json['errors'][0]['detail'] == '{} cannot be found in this OSFGroup'.format(user._id)

            # test user is last manager
            invalid_payload = create_bulk_delete_payload(osf_group._id, manager._id)
            res = app.delete_json_api(url, {'data': [invalid_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'

            # test user is last registered manager
            osf_group.add_unregistered_member('Crazy 8s', 'eight@cos.io', Auth(manager), MANAGER)
            assert len(osf_group.managers) == 2
            res = app.delete_json_api(url, {'data': [invalid_payload]}, auth=manager.auth, expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert res.json['errors'][0]['detail'] == 'Group must have at least one manager.'
