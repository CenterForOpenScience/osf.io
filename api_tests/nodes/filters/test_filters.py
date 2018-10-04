import pytest

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
)
from framework.auth.core import Auth


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
    def parent_project_one(self, user):
        parent_project_one = ProjectFactory(creator=user)
        parent_project_one.title = parent_project_one._id
        parent_project_one.save()
        return parent_project_one

    @pytest.fixture()
    def child_project_one(self, user, parent_project_one):
        return ProjectFactory(
            parent=parent_project_one,
            title='Child of {}'.format(
                parent_project_one._id
            ),
            creator=user)

    @pytest.fixture()
    def project(self, user, parent_project_one):
        return ProjectFactory(
            creator=user,
            title='Neighbor of {}'.format(
                parent_project_one._id
            ))

    @pytest.fixture()
    def parent_project(self, user, contrib):
        parent_project = ProjectFactory(creator=user)
        parent_project.add_contributor(contrib, save=True)
        return parent_project

    @pytest.fixture()
    def child_node_one(self, user, parent_project, parent_project_one):
        return NodeFactory(
            parent=parent_project,
            title='Friend of {}'.format(
                parent_project_one._id
            ),
            creator=user)

    @pytest.fixture()
    def child_node_two(self, user, parent_project):
        return NodeFactory(
            parent=parent_project,
            title='Lait Cafe au Choco',
            creator=user)

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
    def root_ne_url(self, url):
        return '{}filter[root][ne]='.format(url)

    @pytest.fixture()
    def child_of_url(self, url):
        return '{}filter[child_of]='.format(url)

    @pytest.fixture()
    def tags_url(self, url):
        return '{}filter[tags]='.format(url)

    @pytest.fixture()
    def contributors_url(self, url):
        return '{}filter[contributors]='.format(url)

    def test_non_mutating_list_filtering_tests(
            self, app, user, contrib, project,
            parent_project, child_node_one,
            child_node_two, grandchild_node_one,
            grandchild_node_two,
            great_grandchild_node_two,
            root_ne_url, parent_url, root_url,
            contributors_url, parent_project_one,
            child_project_one, child_of_url
    ):

        #   test_parent_filter_null
        expected = [parent_project._id, project._id, parent_project_one._id]
        res = app.get('{}null'.format(parent_url), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    #   test_parent_filter_equals_returns_one
        expected = [grandchild_node_two._id]
        res = app.get(
            '{}{}'.format(
                parent_url,
                child_node_two._id
            ),
            auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    #   test_parent_filter_equals_returns_multiple
        expected = [child_node_one._id, child_node_two._id]
        res = app.get(
            '{}{}'.format(
                parent_url,
                parent_project._id
            ),
            auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    #   test_root_filter_null
        res = app.get(
            '{}null'.format(root_url),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['parameter'] == 'filter'

    #   test_root_filter_equals_returns_branch
        expected = []
        res = app.get(
            '{}{}'.format(
                root_url,
                child_node_two._id
            ),
            auth=user.auth
        )
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    #   test_root_filter_equals_returns_tree
        expected = [
            parent_project._id,
            child_node_one._id,
            child_node_two._id,
            grandchild_node_one._id,
            grandchild_node_two._id,
            great_grandchild_node_two._id]
        res = app.get(
            '{}{}'.format(
                root_url,
                parent_project._id
            ),
            auth=user.auth
        )
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    #   test_contributor_filter
        expected = [parent_project._id]
        res = app.get(
            '{}{}'.format(
                contributors_url,
                contrib._id
            ),
            auth=user.auth
        )
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    #   test_root_ne_excludes_nodes_with_root
        url = '{}{}'.format(root_ne_url, parent_project._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        ids = [node_['id'] for node_ in res.json['data']]

        assert parent_project._id not in ids
        assert child_node_one._id not in ids
        assert child_node_two._id not in ids
        assert project._id in ids

    #   test_root_ne_with_title_excludes_children_with_query_in_title
        url = '{}{}&{}'.format(
            root_ne_url,
            parent_project._id,
            'filter[title]={}'.format(
                parent_project_one.title
            )
        )
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 3
        ids = [node_['id'] for node_ in res.json['data']]
        assert parent_project._id not in ids
        assert child_node_one._id not in ids
        assert child_node_two._id not in ids
        assert project._id in ids

    #   test_root_ne_with_title_id_excludes_children_with_query_in_title_or_id
        id_or_title = 'filter[title,id]={}'.format(parent_project_one._id)
        url = '{}{}&{}'.format(root_ne_url, parent_project._id, id_or_title)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 3
        ids = [node_['id'] for node_ in res.json['data']]
        assert parent_project_one._id in ids
        assert child_project_one._id in ids
        assert project._id in ids
        assert child_node_one._id not in ids
        assert parent_project._id not in ids

    #   test_child_of
        url = '{}{}'.format(
            child_of_url,
            child_node_two._id
        )
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        ids = [node_['id'] for node_ in res.json['data']]
        assert grandchild_node_two._id in ids
        assert great_grandchild_node_two._id in ids

    def test_parent_filter_excludes_linked_nodes(
            self, app, user, parent_project,
            child_node_one, child_node_two,
            parent_url
    ):
        linked_node = NodeFactory()
        parent_project.add_node_link(linked_node, auth=Auth(user))
        expected = [child_node_one._id, child_node_two._id]
        res = app.get(
            '{}{}'.format(
                parent_url,
                parent_project._id
            ),
            auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert linked_node._id not in actual
        assert set(expected) == set(actual)

    def test_tag_filter(self, app, user, parent_project, tags_url):
        parent_project.add_tag(
            'reason',
            auth=Auth(parent_project.creator),
            save=True
        )
        expected = [parent_project._id]
        res = app.get('{}reason'.format(tags_url), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        res = app.get('{}bird'.format(tags_url), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert [] == actual


@pytest.mark.django_db
class NodesListDateFilteringMixin(object):

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node_may(self, user):
        node_may = ProjectFactory(creator=user)
        node_may.created = '2016-05-01 00:00:00.000000+00:00'
        node_may.save()
        return node_may

    @pytest.fixture()
    def node_june(self, user):
        node_june = ProjectFactory(creator=user)
        node_june.created = '2016-06-01 00:00:00.000000+00:00'
        node_june.save()
        return node_june

    @pytest.fixture()
    def node_july(self, user):
        node_july = ProjectFactory(creator=user)
        node_july.created = '2016-07-01 00:00:00.000000+00:00'
        node_july.save()
        return node_july

    @pytest.fixture()
    def created_url(self, url):
        return '{}filter[date_created]='.format(url)

    def test_node_list_date_filter(
            self, app, user, node_may,
            node_june, node_july, url,
            created_url
    ):

        # test_date_filter_equals
        expected = []
        res = app.get('{}{}'.format(created_url, '2016-04-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        expected = [node_may._id]
        res = app.get(
            '{}{}'.format(
                created_url,
                node_may.created
            ),
            auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

    #   test_date_filter_gt
        res_url = '{}filter[date_created][gt]='.format(url)

        expected = []
        res = app.get('{}{}'.format(res_url, '2016-08-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        expected = [node_june._id, node_july._id]
        res = app.get('{}{}'.format(res_url, '2016-05-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    #   test_date_filter_gte
        res_url = '{}filter[date_created][gte]='.format(url)

        expected = []
        res = app.get('{}{}'.format(res_url, '2016-08-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        expected = [node_may._id, node_june._id, node_july._id]
        res = app.get('{}{}'.format(res_url, '2016-05-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    #   test_date_fitler_lt
        res_url = '{}filter[date_created][lt]='.format(url)

        expected = []
        res = app.get('{}{}'.format(res_url, '2016-05-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        expected = [node_may._id, node_june._id]
        res = app.get('{}{}'.format(res_url, '2016-07-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    #   test_date_filter_lte
        res_url = '{}filter[date_created][lte]='.format(url)

        expected = []
        res = app.get('{}{}'.format(res_url, '2016-04-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        expected = [node_may._id, node_june._id, node_july._id]
        res = app.get('{}{}'.format(res_url, '2016-07-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    #   test_date_filter_eq
        res_url = '{}filter[date_created][eq]='.format(url)

        expected = []
        res = app.get('{}{}'.format(res_url, '2016-04-01'), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        expected = [node_may._id]
        res = app.get('{}{}'.format(res_url, node_may.created), auth=user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual
