import pytest

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    NodeRelationFactory,
    ProjectFactory,
)
from osf.utils.auth import Auth


class NodesListFilteringMixin(object):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def parent_project(self, user, contrib):
        parent_project = ProjectFactory(creator=user)
        parent_project.add_contributor(contrib, save=True)
        return parent_project

    @pytest.fixture()
    def child_node_one(self, user, parent_project):
        return NodeFactory(parent=parent_project, creator=user)

    @pytest.fixture()
    def child_node_two(self, user, parent_project):
        return NodeFactory(parent=parent_project, creator=user)

    @pytest.fixture()
    def grandchild_node_one(self, user, child_node_one):
        return NodeFactory(parent=child_node_one, creator=user)

    @pytest.fixture()
    def grandchild_node_two(self, user, child_node_two):
        return NodeFactory(parent=child_node_two, creator=user)

    @pytest.fixture()
    def great_grandchild_node_two(self, user, grandchild_node_two):
        return NodeFactory(parent=grandchild_node_two, creator=user)

    @pytest.fixture()
    def parent_url(self, url):
        return '{}filter[parent]='.format(url)

    @pytest.fixture()
    def root_url(self, url):
        return '{}filter[root]='.format(url)

    @pytest.fixture()
    def tags_url(self, url):
        return '{}filter[tags]='.format(url)

    @pytest.fixture()
    def contributors_url(self, url):
        return '{}filter[contributors]='.format(url)

    def test_non_mutating_list_filtering_tests(self, app, user, contrib, parent_project, child_node_one, child_node_two, grandchild_node_one, grandchild_node_two, great_grandchild_node_two, parent_url, root_url, contributors_url):

    # def test_parent_filter_null(self, app, user, parent_project, parent_url):
        expected = [parent_project._id]
        res = app.get('{}null'.format(parent_url), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    # def test_parent_filter_equals_returns_one(self, app, user, child_node_two, grandchild_node_two, parent_url):
        expected = [grandchild_node_two._id]
        res = app.get('{}{}'.format(parent_url, child_node_two._id), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    # def test_parent_filter_equals_returns_multiple(self, app, user, parent_project, child_node_one, child_node_two, parent_url):
        expected = [child_node_one._id, child_node_two._id]
        res = app.get('{}{}'.format(parent_url, parent_project._id), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    # def test_root_filter_null(self, app, user, root_url):
        res = app.get('{}null'.format(root_url), auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['parameter'] == 'filter'

    # def test_root_filter_equals_returns_branch(self, app, user, child_node_two, root_url):
        expected = []
        res = app.get('{}{}'.format(root_url, child_node_two._id), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    # def test_root_filter_equals_returns_tree(self, app, user, parent_project, child_node_one, child_node_two, grandchild_node_one, grandchild_node_two, great_grandchild_node_two, root_url):
        expected = [parent_project._id, child_node_one._id, child_node_two._id, grandchild_node_one._id, grandchild_node_two._id, great_grandchild_node_two._id]
        res = app.get('{}{}'.format(root_url, parent_project._id), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    # def test_contributor_filter(self, app, user, contrib, parent_project, contributors_url):
        expected = [parent_project._id]
        res = app.get('{}{}'.format(contributors_url, contrib._id), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    def test_parent_filter_excludes_linked_nodes(self, app, user, parent_project, child_node_one, child_node_two, parent_url):
        linked_node = NodeFactory()
        parent_project.add_node_link(linked_node, auth=Auth(user))
        expected = [child_node_one._id, child_node_two._id]
        res = app.get('{}{}'.format(parent_url, parent_project._id), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert linked_node._id not in actual
        assert set(expected) == set(actual)

    def test_tag_filter(self, app, user, parent_project, tags_url):
        parent_project.add_tag('reason', auth=Auth(parent_project.creator), save=True)
        expected = [parent_project._id]
        res = app.get('{}reason'.format(tags_url), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        res = app.get('{}bird'.format(tags_url), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert [] == actual
