import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.filters.test_filters import NodesListFilteringMixin, NodesListDateFilteringMixin
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
    ProjectFactory,
    NodeFactory,
    RegistrationFactory,
)


@pytest.mark.django_db
class TestInstitutionNodeList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def public_node(self, institution):
        public_node = ProjectFactory(is_public=True)
        public_node.affiliated_institutions.add(institution)
        public_node.save()
        return public_node

    @pytest.fixture()
    def user_private_node(self, user, institution):
        user_private_node = ProjectFactory(creator=user, is_public=False)
        user_private_node.affiliated_institutions.add(institution)
        user_private_node.save()
        return user_private_node

    @pytest.fixture()
    def private_node(self, institution):
        private_node = ProjectFactory(is_public=False)
        private_node.affiliated_institutions.add(institution)
        private_node.save()
        return private_node

    @pytest.fixture()
    def institution_node_url(self, institution):
        return '/{0}institutions/{1}/nodes/'.format(API_BASE, institution._id)

    def test_return_all_public_nodes(
            self, app, public_node,
            user_private_node, private_node,
            institution_node_url
    ):
        res = app.get(institution_node_url)

        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_node._id in ids
        assert user_private_node._id not in ids
        assert private_node._id not in ids

    def test_does_not_return_private_nodes_with_auth(
            self, app, user, public_node,
            user_private_node, private_node,
            institution_node_url
    ):
        res = app.get(institution_node_url, auth=user.auth)

        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_node._id in ids
        assert user_private_node._id not in ids
        assert private_node._id not in ids

    def test_registration_not_returned(
            self, app, public_node,
            institution_node_url
    ):
        registration = RegistrationFactory(project=public_node, is_public=True)
        res = app.get(institution_node_url)

        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_node._id in ids
        assert registration._id not in ids

    def test_affiliated_component_with_affiliated_parent_not_returned(
            self, app, user, institution, public_node, institution_node_url):
        # version < 2.2
        component = NodeFactory(parent=public_node, is_public=True)
        component.affiliated_institutions.add(institution)
        component.save()
        res = app.get(institution_node_url, auth=user.auth)
        affiliated_node_ids = [node['id'] for node in res.json['data']]
        assert res.status_code == 200
        assert public_node._id in affiliated_node_ids
        assert component._id not in affiliated_node_ids

    def test_affiliated_component_without_affiliated_parent_not_returned(
            self, app, user, institution, institution_node_url):
        # version < 2.2
        node = ProjectFactory(is_public=True)
        component = NodeFactory(parent=node, is_public=True)
        component.affiliated_institutions.add(institution)
        component.save()
        res = app.get(institution_node_url, auth=user.auth)
        affiliated_node_ids = [x['id'] for x in res.json['data']]
        assert res.status_code == 200
        assert node._id not in affiliated_node_ids
        assert component._id not in affiliated_node_ids

    def test_affiliated_component_with_affiliated_parent_returned(
            self, app, user, institution, public_node, institution_node_url):
        # version 2.2
        component = NodeFactory(parent=public_node, is_public=True)
        component.affiliated_institutions.add(institution)
        component.save()
        url = '{}?version=2.2'.format(institution_node_url)
        res = app.get(url, auth=user.auth)
        affiliated_node_ids = [node['id'] for node in res.json['data']]
        assert res.status_code == 200
        assert public_node._id in affiliated_node_ids
        assert component._id in affiliated_node_ids

    def test_affiliated_component_without_affiliated_parent_returned(
            self, app, user, institution, public_node, institution_node_url):
        # version 2.2
        node = ProjectFactory(is_public=True)
        component = NodeFactory(parent=node, is_public=True)
        component.affiliated_institutions.add(institution)
        component.save()
        url = '{}?version=2.2'.format(institution_node_url)
        res = app.get(url, auth=user.auth)
        affiliated_node_ids = [item['id'] for item in res.json['data']]
        assert res.status_code == 200
        assert node._id not in affiliated_node_ids
        assert component._id in affiliated_node_ids


@pytest.mark.django_db
class TestNodeListFiltering(NodesListFilteringMixin):

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url(self, institution):
        return '/{}institutions/{}/nodes/?version=2.2&'.format(
            API_BASE, institution._id)

    @pytest.fixture()
    def parent_project_one(self, user, institution):
        parent_project_one = ProjectFactory(creator=user, is_public=True)
        parent_project_one.title = parent_project_one._id
        parent_project_one.affiliated_institutions.add(institution)
        parent_project_one.save()
        return parent_project_one

    @pytest.fixture()
    def child_project_one(self, user, parent_project_one, institution):
        child_project_one = ProjectFactory(
            parent=parent_project_one,
            is_public=True,
            title='Child of {}'.format(
                parent_project_one._id),
            creator=user)
        child_project_one.affiliated_institutions.add(institution)
        child_project_one.save()
        return child_project_one

    @pytest.fixture()
    def project(self, user, parent_project_one, institution):
        project = ProjectFactory(
            creator=user,
            title='Neighbor of {}'.format(
                parent_project_one._id),
            is_public=True
        )
        project.affiliated_institutions.add(institution)
        project.save()
        return project

    @pytest.fixture()
    def parent_project(self, user, contrib, institution):
        parent_project = ProjectFactory(creator=user, is_public=True)
        parent_project.add_contributor(contrib, save=False)
        parent_project.affiliated_institutions.add(institution)
        parent_project.save()
        return parent_project

    @pytest.fixture()
    def child_node_one(
            self, user, parent_project,
            institution, parent_project_one
    ):
        child_node_one = NodeFactory(
            parent=parent_project,
            title='Friend of {}'.format(
                parent_project_one._id),
            creator=user,
            is_public=True)
        child_node_one.affiliated_institutions.add(institution)
        child_node_one.save()
        return child_node_one

    @pytest.fixture()
    def child_node_two(self, user, parent_project, institution):
        child_node_two = NodeFactory(
            parent=parent_project,
            creator=user,
            is_public=True)
        child_node_two.affiliated_institutions.add(institution)
        child_node_two.save()
        return child_node_two

    @pytest.fixture()
    def grandchild_node_one(self, user, child_node_one, institution):
        grandchild_node_one = NodeFactory(
            parent=child_node_one, creator=user, is_public=True)
        grandchild_node_one.affiliated_institutions.add(institution)
        grandchild_node_one.save()
        return grandchild_node_one

    @pytest.fixture()
    def grandchild_node_two(self, user, child_node_two, institution):
        grandchild_node_two = NodeFactory(
            parent=child_node_two, creator=user, is_public=True)
        grandchild_node_two.affiliated_institutions.add(institution)
        grandchild_node_two.save()
        return grandchild_node_two

    @pytest.fixture()
    def great_grandchild_node_two(
            self, user, grandchild_node_two,
            institution
    ):
        great_grandchild_node_two = NodeFactory(
            parent=grandchild_node_two, creator=user, is_public=True)
        great_grandchild_node_two.affiliated_institutions.add(institution)
        great_grandchild_node_two.save()
        return great_grandchild_node_two


@pytest.mark.django_db
class TestNodeListDateFiltering(NodesListDateFilteringMixin):

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url(self, institution):
        return '/{}institutions/{}/nodes/?'.format(API_BASE, institution._id)

    @pytest.fixture()
    def node_may(self, user, institution):
        node_may = ProjectFactory(creator=user, is_public=True)
        node_may.created = '2016-05-01 00:00:00.000000+00:00'
        node_may.affiliated_institutions.add(institution)
        node_may.save()
        return node_may

    @pytest.fixture()
    def node_june(self, user, institution):
        node_june = ProjectFactory(creator=user, is_public=True)
        node_june.created = '2016-06-01 00:00:00.000000+00:00'
        node_june.affiliated_institutions.add(institution)
        node_june.save()
        return node_june

    @pytest.fixture()
    def node_july(self, user, institution):
        node_july = ProjectFactory(creator=user, is_public=True)
        node_july.created = '2016-07-01 00:00:00.000000+00:00'
        node_july.affiliated_institutions.add(institution)
        node_july.save()
        return node_july
