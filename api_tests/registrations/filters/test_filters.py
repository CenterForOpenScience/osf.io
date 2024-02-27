from osf.models import Node, Registration
from framework.auth.core import Auth
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
)


class RegistrationListFilteringMixin:

    def setUp(self):
        super().setUp()

        assert self.url, 'Subclasses of RegistrationListFilteringMixin must define self.url'

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.A = ProjectFactory(creator=self.user)
        self.B1 = NodeFactory(parent=self.A, creator=self.user)
        self.B2 = NodeFactory(parent=self.A, creator=self.user)
        self.C1 = NodeFactory(parent=self.B1, creator=self.user)
        self.C2 = NodeFactory(parent=self.B2, creator=self.user)
        self.D2 = NodeFactory(parent=self.C2, creator=self.user)

        self.A.add_contributor(self.user_two, save=True)

        self.node_A = RegistrationFactory(project=self.A, creator=self.user)
        self.node_B2 = RegistrationFactory(project=self.B2, creator=self.user)

        self.parent_url = f'{self.url}filter[parent]='
        self.parent_url_ne = f'{self.url}filter[parent][ne]=null'
        self.root_url = f'{self.url}filter[root]='
        self.tags_url = f'{self.url}filter[tags]='
        self.contributors_url = f'{self.url}filter[contributors]='

    def test_parent_filter_null(self):
        expected = [self.node_A._id, self.node_B2._id]
        res = self.app.get(
            '{}null'.format(
                self.parent_url),
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    def test_parent_filter_ne_null(self):
        expected = list(Registration.objects.exclude(parent_nodes=None).values_list('guids___id', flat=True))
        res = self.app.get(self.parent_url_ne,
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    def test_parent_filter_equals_returns_one(self):
        expected = [n._id for n in self.node_B2.get_nodes()]
        res = self.app.get(
            '{}{}'.format(
                self.parent_url,
                self.node_B2._id),
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert len(actual) == 1
        assert expected == actual

    def test_parent_filter_equals_returns_multiple(self):
        expected = [n._id for n in self.node_A.get_nodes()]
        res = self.app.get(
            '{}{}'.format(
                self.parent_url,
                self.node_A._id),
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert len(actual) == 2
        assert set(expected) == set(actual)

    def test_root_filter_null(self):
        res = self.app.get(
            '{}null'.format(
                self.root_url),
            auth=self.user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['parameter'] == 'filter'

    def test_root_filter_equals_returns_branch(self):
        expected = [n._id for n in Node.objects.get_children(self.node_B2)]
        expected.append(self.node_B2._id)
        res = self.app.get(
            '{}{}'.format(
                self.root_url,
                self.node_B2._id),
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert set(expected) == set(actual)

    def test_root_filter_equals_returns_tree(self):
        expected = [n._id for n in Node.objects.get_children(self.node_A)]
        expected.append(self.node_A._id)
        res = self.app.get(
            '{}{}'.format(
                self.root_url,
                self.node_A._id),
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert len(actual) == 6
        assert set(expected) == set(actual)

    def test_tag_filter(self):
        self.node_A.add_tag('nerd', auth=Auth(self.node_A.creator), save=True)
        expected = [self.node_A._id]
        res = self.app.get(f'{self.tags_url}nerd', auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual

        res = self.app.get(f'{self.tags_url}bird', auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert [] == actual

    def test_contributor_filter(self):
        expected = [self.node_A._id]
        res = self.app.get(
            '{}{}'.format(
                self.contributors_url,
                self.user_two._id),
            auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert expected == actual
