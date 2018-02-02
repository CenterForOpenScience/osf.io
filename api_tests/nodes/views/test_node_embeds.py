import functools
import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory
)
from rest_framework import exceptions


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeEmbeds:

    @pytest.fixture()
    def write_contrib_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contribs(self, write_contrib_one, write_contrib_two):
        return [write_contrib_one, write_contrib_two]

    @pytest.fixture()
    def auth(self, user):
        return Auth(user)

    @pytest.fixture()
    def make_public_node(self, user):
        return functools.partial(ProjectFactory, is_public=False, creator=user)

    @pytest.fixture()
    def root_node(
            self, auth, write_contrib_one,
            write_contrib_two, make_public_node):
        root_node = make_public_node()
        root_node.add_contributor(
            write_contrib_one, ['read', 'write'],
            auth=auth, save=True)
        root_node.add_contributor(
            write_contrib_two, ['read', 'write'],
            auth=auth, save=True)
        return root_node

    @pytest.fixture()
    def child_one(
            self, auth, write_contrib_one,
            write_contrib_two, make_public_node,
            root_node):
        child_one = make_public_node(parent=root_node)
        child_one.add_contributor(
            write_contrib_one, ['read', 'write'],
            auth=auth, save=True)
        child_one.add_contributor(
            write_contrib_two, ['read', 'write'],
            auth=auth, save=True)
        return child_one

    @pytest.fixture()
    def child_two(self, make_public_node, root_node):
        return make_public_node(parent=root_node)

    @pytest.fixture()
    def subchild(self, child_two, write_contrib_one):
        return ProjectFactory(parent=child_two, creator=write_contrib_one)

    def test_node_embeds(
            self, app, user, write_contrib_one,
            write_contribs, subchild, root_node,
            child_one, child_two):

        #   test_embed_children
        url = '/{}nodes/{}/?embed=children'.format(API_BASE, root_node._id)

        res = app.get(url, auth=user.auth)
        embeds = res.json['data']['embeds']
        ids = [child_one._id, child_two._id]
        assert len(embeds['children']['data']) == len(ids)
        children = [
            child['id'] for child in res.json['data']['embeds']['children']['data']
        ]
        assert set([child_one._id, child_two._id]) == set(children)

    #   test_embed_parent
        url = '/{}nodes/{}/?embed=parent'.format(API_BASE, child_one._id)

        res = app.get(url, auth=user.auth)
        embeds = res.json['data']['embeds']
        assert embeds['parent']['data']['id'] == root_node._id

    #   test_embed_no_parent
        url = '/{}nodes/{}/?embed=parent'.format(API_BASE, root_node._id)

        res = app.get(url, auth=user.auth)
        data = res.json['data']
        assert 'embeds' not in data

    #   test_embed_contributors
        url = '/{}nodes/{}/?embed=contributors'.format(API_BASE, child_one._id)

        res = app.get(url, auth=user.auth)
        embeds = res.json['data']['embeds']
        all_contribs = write_contribs + [user]
        formatted_ids = [
            '{}-{}'.format(
                child_one._id, contrib._id
            )for contrib in all_contribs]
        embed_contrib_ids = [
            contrib['id']for contrib in embeds['contributors']['data']
        ]
        assert set(formatted_ids) == set(embed_contrib_ids)

    #   test_embed_children_filters_unauthorized
        url = '/{}nodes/{}/?embed=children'.format(API_BASE, root_node._id)

        res = app.get(url, auth=write_contrib_one.auth)
        embeds = res.json['data']['embeds']
        ids = [c['id'] for c in embeds['children']['data']]
        assert child_two._id not in ids
        assert child_one._id in ids

    #   test_embed_parent_unauthorized
        url = '/{}nodes/{}/?embed=parent'.format(API_BASE, subchild._id)

        res = app.get(url, auth=write_contrib_one.auth)
        assert 'errors' in res.json['data']['embeds']['parent']
        assert res.json['data']['embeds']['parent']['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_embed_attributes_not_relationships
        url = '/{}nodes/{}/?embed=title'.format(API_BASE, root_node._id)

        res = app.get(url, auth=write_contrib_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The following fields are not embeddable: title'

    #   test_embed_contributors_pagination
        url = '/{}nodes/{}/?embed=contributors'.format(API_BASE, root_node._id)
        res = app.get(url, auth=write_contrib_one.auth)
        assert res.status_code == 200
        assert res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic'] == 3

    #   test_embed_contributors_updated_pagination
        url = '/{}nodes/{}/?version=2.1&embed=contributors'.format(
            API_BASE, root_node._id)
        res = app.get(url, auth=write_contrib_one.auth)
        assert res.status_code == 200
        assert res.json['data']['embeds']['contributors']['meta']['total_bibliographic'] == 3
