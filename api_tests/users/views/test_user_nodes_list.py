import pytest

from django.utils.timezone import now

from api.base.settings.defaults import API_BASE
from api_tests.nodes.filters.test_filters import NodesListFilteringMixin, NodesListDateFilteringMixin
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    PreprintFactory,
    ProjectFactory,
    RegistrationFactory,
)
from website.views import find_bookmark_collection


@pytest.mark.django_db
class TestUserNodes:

    @pytest.fixture()
    def user_one(self):
        user_one = AuthUserFactory()
        user_one.social['twitter'] = 'RheisenDennis'
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project_user_one(self, user_one):
        return ProjectFactory(
            title='Public Project User One',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def private_project_user_one(self, user_one):
        return ProjectFactory(
            title='Private Project User One',
            is_public=False,
            creator=user_one)

    @pytest.fixture()
    def public_project_user_two(self, user_two):
        return ProjectFactory(
            title='Public Project User Two',
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def private_project_user_two(self, user_two):
        return ProjectFactory(
            title='Private Project User Two',
            is_public=False,
            creator=user_two)

    @pytest.fixture()
    def deleted_project_user_one(self, user_one):
        return CollectionFactory(
            title='Deleted Project User One',
            is_public=False,
            creator=user_one,
            deleted=now())

    @pytest.fixture()
    def folder(self):
        return CollectionFactory()

    @pytest.fixture()
    def deleted_folder(self, user_one):
        return CollectionFactory(
            title='Deleted Folder User One',
            is_public=False,
            creator=user_one,
            deleted=now())

    @pytest.fixture()
    def bookmark_collection(self, user_one):
        return find_bookmark_collection(user_one)

    @pytest.fixture()
    def registration(self, user_one, public_project_user_one):
        return RegistrationFactory(
            project=public_project_user_one,
            creator=user_one,
            is_public=True)

    def test_user_nodes(
            self, app, user_one, user_two,
            public_project_user_one,
            public_project_user_two,
            private_project_user_one,
            private_project_user_two,
            deleted_project_user_one,
            folder, deleted_folder, registration):

        #   test_authorized_in_gets_200
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_anonymous_gets_200
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_get_projects_logged_in
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_user_one._id in ids
        assert private_project_user_one._id in ids
        assert public_project_user_two._id not in ids
        assert private_project_user_two._id not in ids
        assert folder._id not in ids
        assert deleted_folder._id not in ids
        assert deleted_project_user_one._id not in ids
        assert registration._id not in ids

    #   test_get_projects_not_logged_in
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_user_one._id in ids
        assert private_project_user_one._id not in ids
        assert public_project_user_two._id not in ids
        assert private_project_user_two._id not in ids
        assert folder._id not in ids
        assert deleted_project_user_one._id not in ids
        assert registration._id not in ids

    #   test_get_projects_logged_in_as_different_user
        url = '/{}users/{}/nodes/'.format(API_BASE, user_two._id)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_user_two._id in ids
        assert public_project_user_one._id not in ids
        assert private_project_user_one._id not in ids
        assert private_project_user_two._id not in ids
        assert folder._id not in ids
        assert deleted_project_user_one._id not in ids
        assert registration._id not in ids

        url = '/{}users/{}/nodes/?sort=-title'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)

        node_json = res.json['data']

        ids = [each['id'] for each in node_json]

        assert public_project_user_one._id == ids[0]
        assert private_project_user_one._id == ids[1]

        url = '/{}users/{}/nodes/?sort=title'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)

        node_json = res.json['data']

        ids = [each['id'] for each in node_json]

        assert public_project_user_one._id == ids[1]
        assert private_project_user_one._id == ids[0]


@pytest.mark.django_db
class TestUserNodesPreprintsFiltering:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def no_preprints_node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def valid_preprint_node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def orphaned_preprint_node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def abandoned_preprint_node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def valid_preprint(self, valid_preprint_node):
        return PreprintFactory(project=valid_preprint_node)

    @pytest.fixture()
    def abandoned_preprint(self, abandoned_preprint_node):
        return PreprintFactory(
            project=abandoned_preprint_node,
            is_published=False)

    @pytest.fixture()
    def orphaned_preprint(self, orphaned_preprint_node):
        orphaned_preprint = PreprintFactory(project=orphaned_preprint_node)
        orphaned_preprint.node.preprint_file = None
        orphaned_preprint.node.save()
        return orphaned_preprint

    @pytest.fixture()
    def url_base(self):
        return '/{}users/me/nodes/?filter[preprint]='.format(API_BASE)

    def test_filter_false(
            self, app, user, abandoned_preprint_node,
            no_preprints_node, orphaned_preprint_node, url_base):
        expected_ids = [
            abandoned_preprint_node._id,
            no_preprints_node._id,
            orphaned_preprint_node._id]
        res = app.get('{}false'.format(url_base), auth=user.auth)
        actual_ids = [n['id'] for n in res.json['data']]

        assert set(expected_ids) == set(actual_ids)

    def test_filter_true(
            self, app, user, valid_preprint_node,
            valid_preprint, url_base):
        expected_ids = [valid_preprint_node._id]
        res = app.get('{}true'.format(url_base), auth=user.auth)
        actual_ids = [n['id'] for n in res.json['data']]

        assert set(expected_ids) == set(actual_ids)


@pytest.mark.django_db
class TestNodeListFiltering(NodesListFilteringMixin):

    @pytest.fixture()
    def url(self):
        return '/{}users/me/nodes/?'.format(API_BASE)


@pytest.mark.django_db
class TestNodeListDateFiltering(NodesListDateFilteringMixin):

    @pytest.fixture()
    def url(self):
        return '/{}users/me/nodes/?'.format(API_BASE)
