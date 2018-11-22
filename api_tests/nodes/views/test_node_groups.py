import pytest
from guardian.shortcuts import get_perms

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    OSFGroupFactory,
)

@pytest.fixture()
def write_contrib():
    return AuthUserFactory()

@pytest.fixture()
def read_contrib():
    return AuthUserFactory()

@pytest.fixture()
def non_contrib():
    return AuthUserFactory()

@pytest.fixture()
def member():
    return AuthUserFactory()

@pytest.fixture()
def manager():
    return AuthUserFactory()

@pytest.fixture()
def osf_group(member, manager):
    group = OSFGroupFactory(creator=manager, name='Platform Team')
    group.make_member(member, auth=Auth(manager))
    return group

@pytest.fixture()
def private_project(write_contrib, read_contrib):
    project = ProjectFactory(is_public=False)
    project.add_contributor(read_contrib, permissions='read')
    project.add_contributor(write_contrib, permissions='write', save=True)
    return project

@pytest.fixture()
def public_project(write_contrib, read_contrib):
    project = ProjectFactory(is_public=True)
    project.add_contributor(read_contrib, permissions='read')
    project.add_contributor(write_contrib, permissions='write', save=True)
    return project

@pytest.fixture()
def public_url(public_project):
    return '/{}nodes/{}/groups/'.format(API_BASE, public_project._id)

@pytest.fixture()
def private_url(private_project):
    return '/{}nodes/{}/groups/'.format(API_BASE, private_project._id)

@pytest.fixture()
def public_detail_url(public_url, osf_group):
    return '{}{}/'.format(public_url, osf_group._id)

@pytest.fixture()
def make_node_group_payload():
    def payload(attributes, relationships=None):
        payload_data = {
            'data': {
                'type': 'node-groups',
                'attributes': attributes,
            }
        }
        if relationships:
            payload_data['data']['relationships'] = relationships

        return payload_data
    return payload


@pytest.mark.django_db
class TestNodeGroupsList:

    @pytest.fixture()
    def make_group_id(self):
        def contrib_id(node, group):
            return '{}-{}'.format(node._id, group._id)
        return contrib_id

    def test_return(self, app, non_contrib, osf_group, member, manager, public_project, private_project, public_url, private_url, make_group_id):
        public_project.add_osf_group(osf_group, 'write')

        # public url logged out
        res = app.get(public_url)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(public_project, osf_group) in ids
        assert resp_json[0]['attributes']['permission'] == 'write'

        # private project logged in
        private_project.add_osf_group(osf_group, 'read')
        res = app.get(private_url, auth=private_project.creator.auth)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(private_project, osf_group) in ids
        assert resp_json[0]['attributes']['permission'] == 'read'

        # private project logged out
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401

        # private project non_contrib
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # private project group_member
        res = app.get(private_url, auth=member.auth, expect_errors=True)
        assert res.status_code == 200

        # private project group_manager
        res = app.get(private_url, auth=member.auth, expect_errors=True)
        assert res.status_code == 200

    def test_filter_groups(self, app, osf_group, private_project, manager, private_url, make_group_id):
        read_group = OSFGroupFactory(creator=manager, name='house')
        write_group = OSFGroupFactory(creator=manager, name='doghouse')
        private_project.add_osf_group(read_group, 'read')
        private_project.add_osf_group(write_group, 'write')
        private_project.add_osf_group(osf_group, 'admin')

        # test filter on permission
        url = private_url + '?filter[permission]=admin'
        res = app.get(url, auth=private_project.creator.auth)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(private_project, osf_group) in ids
        assert make_group_id(private_project, write_group) not in ids
        assert make_group_id(private_project, read_group) not in ids

        url = private_url + '?filter[permission]=write'
        res = app.get(url, auth=private_project.creator.auth)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(private_project, osf_group) in ids
        assert make_group_id(private_project, write_group) in ids
        assert make_group_id(private_project, read_group) not in ids

        url = private_url + '?filter[permission]=read'
        res = app.get(url, auth=private_project.creator.auth)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(private_project, osf_group) in ids
        assert make_group_id(private_project, write_group) in ids
        assert make_group_id(private_project, read_group) in ids

        # test_filter_on_invalid_permission
        url = private_url + '?filter[permission]=bad_perm'
        res = app.get(url, auth=private_project.creator.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'bad_perm is not a filterable permission.'

        url = private_url + '?filter[name]=Plat'
        res = app.get(url, auth=private_project.creator.auth)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(private_project, osf_group) in ids
        assert make_group_id(private_project, write_group) not in ids
        assert make_group_id(private_project, read_group) not in ids

        url = private_url + '?filter[name]=house'
        res = app.get(url, auth=private_project.creator.auth)
        resp_json = res.json['data']
        ids = [each['id'] for each in resp_json]
        assert make_group_id(private_project, osf_group) not in ids
        assert make_group_id(private_project, write_group) in ids
        assert make_group_id(private_project, read_group) in ids


@pytest.mark.django_db
class TestNodeGroupCreate:

    def test_create_node_groups(self, app, osf_group, public_url, non_contrib, member, manager,
                                public_project, write_contrib, make_node_group_payload):
        attributes = {'permission': 'write'}
        relationships = {
            'osf_groups': {
                'data': {
                    'type': 'osf_groups',
                    'id': osf_group._id,
                }
            }
        }
        payload = make_node_group_payload(attributes=attributes, relationships=relationships)

        # test add group noncontrib fails
        res = app.post_json_api(public_url, payload, auth=non_contrib, expect_errors=True)
        assert res.status_code == 401

        # add group with write permissions fails
        res = app.post_json_api(public_url, payload, auth=write_contrib, expect_errors=True)
        assert res.status_code == 401

        # add group with admin on node but not manager in group
        res = app.post_json_api(public_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 403

        # create group with admin permissions on node and manager permissions in group
        public_project.add_contributor(manager, permissions='admin', auth=Auth(public_project.creator), save=True)

        # test_perm_not_specified - given write by default
        relationship_only = make_node_group_payload(attributes={}, relationships=relationships)
        res = app.post_json_api(public_url, relationship_only, auth=manager.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['permission'] == 'write'
        assert osf_group._id in res.json['data']['relationships']['osf_groups']['links']['related']['href']

        public_project.remove_osf_group(osf_group)

        # test_relationship_not_specified
        attributes_only = make_node_group_payload(attributes=attributes)
        res = app.post_json_api(public_url, attributes_only, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'OSFGroup relationship must be specified.'

        # test_admin_perms
        res = app.post_json_api(public_url, payload, auth=manager.auth)
        assert public_project in osf_group.nodes
        assert public_project.has_permission(member, 'write')
        assert res.json['data']['attributes']['permission'] == 'write'
        assert osf_group._id in res.json['data']['relationships']['osf_groups']['links']['related']['href']

        # test creating group a second time fails
        res = app.post_json_api(public_url, payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The OSF group {} has already been added to the node {}'.format(
            osf_group._id, public_project._id
        )

        # test incorrect permission string
        public_project.remove_osf_group(osf_group)
        payload['data']['attributes']['permission'] = 'not a real perm'
        res = app.post_json_api(public_url, payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'not a real perm is not a valid permission.'

        # test_incorrect_type
        payload['data']['type'] = 'incorrect_type'
        res = app.post_json_api(public_url, payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 409

        # test not a real group
        payload['data']['type'] = 'node-groups'
        payload['data']['relationships']['osf_groups']['data']['id'] = 'not_a_real_group_id'
        res = app.post_json_api(public_url, payload, auth=manager.auth, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestNodeGroupDetail:

    def test_node_group_detail(self, app, public_detail_url, osf_group, public_project):
        # res for group not attached to node raised permissions error
        res = app.get(public_detail_url, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'OSF Group {} does not have permissions to node {}.'.format(osf_group._id, public_project._id)

        public_project.add_osf_group(osf_group, 'write')

        # test attributes
        res = app.get(public_detail_url)
        attributes = res.json['data']['attributes']
        assert attributes['date_created'] == osf_group.created.replace(tzinfo=None).isoformat()
        assert attributes['date_modified'] == osf_group.modified.replace(tzinfo=None).isoformat()
        assert attributes['name'] == osf_group.name
        assert attributes['permission'] == 'write'

        # test relationships
        relationships = res.json['data']['relationships']
        assert relationships.keys() == ['osf_groups']
        assert osf_group._id in relationships['osf_groups']['links']['related']['href']

        # get group that does not exist
        res = app.get(public_detail_url.replace(osf_group._id, 'hellonotarealroute'), expect_errors=True)
        assert res.status_code == 404

    def test_node_group_detail_perms(self, app, non_contrib, osf_group, member, public_project, private_project, public_detail_url, private_url):
        public_project.add_osf_group(osf_group, 'read')
        private_project.add_osf_group(osf_group, 'write')
        private_detail_url = private_url + osf_group._id + '/'

        # nonauth
        res = app.get(private_detail_url, expect_errors=True)
        assert res.status_code == 401

        res = app.get(public_detail_url)
        assert res.status_code == 200

        # noncontrib
        res = app.get(private_detail_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.get(public_detail_url, auth=non_contrib.auth)
        assert res.status_code == 200

        # member
        res = app.get(private_detail_url, auth=member.auth)
        assert res.status_code == 200

        res = app.get(public_detail_url, auth=member.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestNodeGroupUpdate:

    def test_update_permission(self, app, public_detail_url, osf_group, write_contrib, non_contrib,
                                public_project, make_node_group_payload):
        attributes = {'permission': 'write'}
        payload = make_node_group_payload(attributes=attributes)

        # group has not been added to the node
        res = app.patch_json_api(public_detail_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 404

        public_project.add_osf_group(osf_group, 'read')

        # test id not present in request
        res = app.patch_json_api(public_detail_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 400

        # test passing invalid group_id to update
        payload['data']['id'] = 'nope'
        res = app.patch_json_api(public_detail_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 409

        payload['data']['id'] = public_project._id + '-' + osf_group._id

        # test update not logged in fails
        res = app.patch_json_api(public_detail_url, payload, expect_errors=True)
        assert res.status_code == 401

        # test update noncontrib in fails
        res = app.patch_json_api(public_detail_url, payload, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test update as node write contrib fails
        res = app.patch_json_api(public_detail_url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test update as node admin
        res = app.patch_json_api(public_detail_url, payload, auth=public_project.creator.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert not osf_group.is_member(public_project.creator.auth)
        assert res_json['attributes']['permission'] == 'write'
        assert 'write_node' in get_perms(osf_group.member_group, public_project)

        # test update invalid perm
        payload['data']['attributes']['permission'] = 'bad_perm'
        res = app.patch_json_api(public_detail_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'bad_perm is not a valid permission.'

        # test update no perm specified, perms unchanged
        payload['data']['attributes'] = {}
        res = app.patch_json_api(public_detail_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 200
        assert res_json['attributes']['permission'] == 'write'


@pytest.mark.django_db
class TestNodeGroupDelete:

    def test_delete_group(self, app, public_detail_url, public_project, osf_group, member, manager, non_contrib, write_contrib):
        public_project.add_contributor(manager, permissions='admin')
        payload = {
            'data': [
                {'type': 'node-groups', 'id': '{}-{}'.format(public_project._id, osf_group._id)}
            ]
        }
        # group has not been added to the node
        res = app.delete_json_api(public_detail_url, payload, auth=public_project.creator.auth, expect_errors=True)
        assert res.status_code == 404

        public_project.add_osf_group(osf_group, 'write')

        # test member with write permission cannot remove group
        res = app.delete_json_api(public_detail_url, payload, auth=member.auth, expect_errors=True)
        assert res.status_code == 403

        # not logged in user cannot remove group
        res = app.delete_json_api(public_detail_url, payload, expect_errors=True)
        assert res.status_code == 401

        # non contributor cannot remove group
        res = app.delete_json_api(public_detail_url, payload, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # write contributor cannot remove group
        res = app.delete_json_api(public_detail_url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test manager on group can remove group
        res = app.delete_json_api(public_detail_url, payload, auth=manager.auth)
        assert res.status_code == 204
        assert osf_group not in public_project.osf_groups

        # test member with admin permissions can remove group
        public_project.add_osf_group(osf_group, 'admin')
        res = app.delete_json_api(public_detail_url, payload, auth=member.auth)
        assert res.status_code == 204
        assert osf_group not in public_project.osf_groups

        second_group = OSFGroupFactory(creator=non_contrib)
        second_group.make_member(member)
        public_project.add_osf_group(second_group, 'write')

        # test member with write cannot remove group
        second_payload = {
            'data': [
                {'type': 'node-groups', 'id': '{}-{}'.format(public_project._id, second_group._id)}
            ]
        }
        second_url = '/{}nodes/{}/groups/{}/'.format(API_BASE, public_project._id, second_group._id)
        res = app.delete_json_api(second_url, second_payload, auth=member.auth, expect_errors=True)
        assert res.status_code == 403

        # test manager can remove the group (even though they are not an admin contributor)
        res = app.delete_json_api(second_url, second_payload, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 204
        assert second_group not in public_project.osf_groups
