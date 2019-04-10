import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory,
)
from osf.utils import permissions


@pytest.fixture()
def admin():
    return AuthUserFactory()


@pytest.fixture()
def read_contrib():
    return AuthUserFactory()


@pytest.fixture()
def write_contrib():
    return AuthUserFactory()


@pytest.fixture()
def valid_contributors(admin, read_contrib, write_contrib):
    return [
        admin._id,
        read_contrib._id,
        write_contrib._id,
    ]


@pytest.fixture()
def private_node_one(admin, read_contrib, write_contrib):
    private_node_one = ProjectFactory(
        is_public=False,
        creator=admin,
        title='Private One')
    private_node_one.add_contributor(
        read_contrib, permissions=[
            permissions.READ], save=True)
    private_node_one.add_contributor(
        write_contrib,
        permissions=[
            permissions.READ,
            permissions.WRITE],
        save=True)
    return private_node_one


@pytest.fixture()
def private_node_one_anonymous_link(private_node_one):
    private_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
    private_node_one_anonymous_link.nodes.add(private_node_one)
    private_node_one_anonymous_link.save()
    return private_node_one_anonymous_link


@pytest.fixture()
def private_node_one_private_link(private_node_one):
    private_node_one_private_link = PrivateLinkFactory(anonymous=False)
    private_node_one_private_link.nodes.add(private_node_one)
    private_node_one_private_link.save()
    return private_node_one_private_link


@pytest.fixture()
def private_node_one_url(private_node_one):
    return '/{}nodes/{}/'.format(API_BASE, private_node_one._id)


@pytest.fixture()
def private_node_two(admin, read_contrib, write_contrib):
    private_node_two = ProjectFactory(
        is_public=False,
        creator=admin,
        title='Private Two')
    private_node_two.add_contributor(
        read_contrib, permissions=[permissions.READ], save=True)
    private_node_two.add_contributor(
        write_contrib,
        permissions=[
            permissions.READ,
            permissions.WRITE],
        save=True)
    return private_node_two


@pytest.fixture()
def private_node_two_url(private_node_two):
    return '/{}nodes/{}/'.format(API_BASE, private_node_two._id)


@pytest.fixture()
def public_node_one(admin, read_contrib, write_contrib):
    public_node_one = ProjectFactory(
        is_public=True, creator=admin, title='Public One')
    public_node_one.add_contributor(
        read_contrib, permissions=[permissions.READ], save=True)
    public_node_one.add_contributor(
        write_contrib,
        permissions=[
            permissions.READ,
            permissions.WRITE],
        save=True)
    return public_node_one


@pytest.fixture()
def public_node_one_anonymous_link(public_node_one):
    public_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
    public_node_one_anonymous_link.nodes.add(public_node_one)
    public_node_one_anonymous_link.save()
    return public_node_one_anonymous_link


@pytest.fixture()
def public_node_one_private_link(public_node_one):
    public_node_one_private_link = PrivateLinkFactory(anonymous=False)
    public_node_one_private_link.nodes.add(public_node_one)
    public_node_one_private_link.save()
    return public_node_one_private_link


@pytest.fixture()
def public_node_one_url(public_node_one):
    return '/{}nodes/{}/'.format(API_BASE, public_node_one._id)


@pytest.fixture()
def public_node_two(admin, read_contrib, write_contrib):
    public_node_two = ProjectFactory(
        is_public=True, creator=admin, title='Public Two')
    public_node_two.add_contributor(
        read_contrib, permissions=[permissions.READ], save=True)
    public_node_two.add_contributor(
        write_contrib,
        permissions=[
            permissions.READ,
            permissions.WRITE],
        save=True)
    return public_node_two


@pytest.fixture()
def public_node_two_url(public_node_two):
    return '/{}nodes/{}/'.format(API_BASE, public_node_two._id)


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'admin',
    'read_contrib',
    'write_contrib',
    'valid_contributors',
    'private_node_one',
    'private_node_one_anonymous_link',
    'private_node_one_private_link',
    'private_node_one_url',
    'private_node_two',
    'private_node_two_url',
    'public_node_one',
    'public_node_one_anonymous_link',
    'public_node_one_private_link',
    'public_node_one_url',
    'public_node_two',
    'public_node_two_url')
class TestNodeDetailViewOnlyLinks:

    def test_private_node(
            self, app, admin, read_contrib, valid_contributors,
            private_node_one, private_node_one_url,
            private_node_one_private_link,
            private_node_one_anonymous_link,
            public_node_one_url,
            public_node_one_private_link,
            public_node_one_anonymous_link):

        #   test_private_node_with_link_works_when_using_link
        res_normal = app.get(private_node_one_url, auth=read_contrib.auth)
        assert res_normal.status_code == 200
        res_linked = app.get(
            private_node_one_url,
            {'view_only': private_node_one_private_link.key})
        assert res_linked.status_code == 200
        assert res_linked.json['data']['attributes']['current_user_permissions'] == [
            'read']

        # Remove any keys that will be different for view-only responses
        res_normal_json = res_normal.json
        res_linked_json = res_linked.json
        user_can_comment = res_normal_json['data']['attributes'].pop(
            'current_user_can_comment')
        view_only_can_comment = res_linked_json['data']['attributes'].pop(
            'current_user_can_comment')

        assert user_can_comment
        assert not view_only_can_comment

    #   test_private_node_with_link_unauthorized_when_not_using_link
        res = app.get(private_node_one_url, expect_errors=True)
        assert res.status_code == 401

    #   test_private_node_with_link_anonymous_does_not_expose_contributor_id
        res = app.get(private_node_one_url, {
            'view_only': private_node_one_anonymous_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'] == ''

    #   test_private_node_with_link_non_anonymous_does_expose_contributor_id
        res = app.get(private_node_one_url, {
            'view_only': private_node_one_private_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in valid_contributors

    #   test_private_node_logged_in_with_anonymous_link_does_not_expose_contributor_id
        res = app.get(private_node_one_url, {
            'view_only': private_node_one_private_link.key,
            'embed': 'contributors',
        }, auth=admin.auth)
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in valid_contributors

    #   test_public_node_with_link_anonymous_does_not_expose_user_id
        res = app.get(public_node_one_url, {
            'view_only': public_node_one_anonymous_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'] == ''

    #   test_public_node_with_link_non_anonymous_does_expose_contributor_id
        res = app.get(public_node_one_url, {
            'view_only': public_node_one_private_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in valid_contributors

    #   test_public_node_with_link_unused_does_expose_contributor_id
        res = app.get(public_node_one_url, {
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in valid_contributors

    #   test_view_only_link_does_not_grant_write_permission
        payload = {
            'data': {
                'attributes': {
                    'title': 'Cannot touch this'},
                'id': private_node_one._id,
                'type': 'nodes',
            }
        }
        res = app.patch_json_api(private_node_one_url, payload, {
            'view_only': private_node_one_private_link.key,
        }, expect_errors=True)
        assert res.status_code == 401

    #   test_view_only_link_from_anther_project_does_not_grant_view_permission
        res = app.get(private_node_one_url, {
            'view_only': public_node_one_private_link.key,
        }, expect_errors=True)
        assert res.status_code == 401

    #   test_private_project_logs_with_anonymous_link_does_not_expose_user_id
        res = app.get(private_node_one_url + 'logs/', {
            'view_only': str(private_node_one_anonymous_link.key),
        })
        assert res.status_code == 200
        body = res.body
        for id in valid_contributors:
            assert id not in body

    #   test_private_project_with_anonymous_link_does_not_expose_registrations_or_forks
        res = app.get(private_node_one_url, {
            'view_only': private_node_one_anonymous_link.key,
        })
        assert res.status_code == 200
        relationships = res.json['data']['relationships']
        if 'embeds' in res.json['data']:
            embeds = res.json['data']['embeds']
        else:
            embeds = {}
        assert 'registrations' not in relationships
        assert 'forks' not in relationships, 'Add forks view to blacklist in hide_view_when_anonymous().'
        assert 'registrations' not in embeds
        assert 'forks' not in embeds, 'Add forks view to blacklist in hide_view_when_anonymous().'

    #   test_bad_view_only_link_does_not_modify_permissions
        res = app.get(private_node_one_url + 'logs/', {
            'view_only': 'thisisnotarealprivatekey',
        }, expect_errors=True)
        assert res.status_code == 401
        res = app.get(private_node_one_url + 'logs/', {
            'view_only': 'thisisnotarealprivatekey',
        }, auth=admin.auth)
        assert res.status_code == 200

    #   test_view_only_key_in_relationships_links
        res = app.get(
            private_node_one_url,
            {'view_only': private_node_one_private_link.key})
        assert res.status_code == 200
        res_relationships = res.json['data']['relationships']
        for key, value in res_relationships.items():
            if isinstance(value, list):
                for relationship in value:
                    links = relationship.get('links', {})
                    if links.get('related', False):
                        assert private_node_one_private_link.key in links['related']['href']
                    if links.get('self', False):
                        assert private_node_one_private_link.key in links['self']['href']
            else:
                links = value.get('links', {})
                if links.get('related', False):
                    assert private_node_one_private_link.key in links['related']['href']
                if links.get('self', False):
                    assert private_node_one_private_link.key in links['self']['href']

    #   test_view_only_key_in_self_and_html_links
        res = app.get(
            private_node_one_url,
            {'view_only': private_node_one_private_link.key})
        assert res.status_code == 200
        links = res.json['data']['links']
        assert private_node_one_private_link.key in links['self']
        assert private_node_one_private_link.key in links['html']


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'admin',
    'read_contrib',
    'write_contrib',
    'valid_contributors',
    'private_node_one',
    'private_node_one_anonymous_link',
    'private_node_one_private_link',
    'private_node_one_url',
    'private_node_two',
    'private_node_two_url',
    'public_node_one',
    'public_node_one_anonymous_link',
    'public_node_one_private_link',
    'public_node_one_url',
    'public_node_two',
    'public_node_two_url')
class TestNodeListViewOnlyLinks:

    def test_node_list_view_only_links(
            self, app, valid_contributors,
            private_node_one,
            private_node_one_private_link,
            private_node_one_anonymous_link):

        #   test_private_link_does_not_show_node_in_list
        res = app.get('/{}nodes/'.format(API_BASE), {
            'view_only': private_node_one_private_link.key,
        })
        assert res.status_code == 200
        nodes = res.json['data']
        node_ids = []
        for node in nodes:
            node_ids.append(node['id'])
        assert private_node_one._id not in node_ids

    #   test_anonymous_link_does_not_show_contributor_id_in_node_list
        res = app.get('/{}nodes/'.format(API_BASE), {
            'view_only': private_node_one_anonymous_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        nodes = res.json['data']
        assertions = 0
        for node in nodes:
            contributors = node['embeds']['contributors']['data']
            for contributor in contributors:
                assertions += 1
                assert contributor['id'] == ''
        assert assertions != 0

    #   test_non_anonymous_link_does_show_contributor_id_in_node_list
        res = app.get('/{}nodes/'.format(API_BASE), {
            'view_only': private_node_one_private_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        nodes = res.json['data']
        assertions = 0
        for node in nodes:
            contributors = node['embeds']['contributors']['data']
            for contributor in contributors:
                assertions += 1
                assert contributor['id'].split('-')[1] in valid_contributors
        assert assertions != 0
