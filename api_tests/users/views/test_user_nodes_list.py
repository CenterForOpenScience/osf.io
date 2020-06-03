import pytest

from django.utils.timezone import now

from api.base.settings.defaults import API_BASE
from api_tests.nodes.filters.test_filters import NodesListFilteringMixin, NodesListDateFilteringMixin
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    OSFGroupFactory,
    PreprintFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
)
from website.views import find_bookmark_collection
from osf.utils import permissions
from osf.utils.workflows import DefaultStates


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

    # test_osf_group_member_node_shows_up_in_user_nodes
        group_mem = AuthUserFactory()
        url = '/{}users/{}/nodes/'.format(API_BASE, group_mem._id)
        res = app.get(url, auth=group_mem.auth)
        assert len(res.json['data']) == 0

        group = OSFGroupFactory(creator=group_mem)
        private_project_user_one.add_osf_group(group, permissions.READ)
        res = app.get(url, auth=group_mem.auth)
        assert len(res.json['data']) == 1

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 1

        private_project_user_one.delete()
        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0


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
    def abandoned_preprint_node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def valid_preprint(self, valid_preprint_node):
        return PreprintFactory(project=valid_preprint_node)

    @pytest.fixture()
    def abandoned_preprint(self, abandoned_preprint_node):
        preprint = PreprintFactory(project=abandoned_preprint_node,
            is_published=False)
        preprint.machine_state = DefaultStates.INITIAL.value
        return preprint

    @pytest.fixture()
    def url_base(self):
        return '/{}users/me/nodes/?filter[preprint]='.format(API_BASE)

    def test_filter_false(
            self, app, user, abandoned_preprint_node, abandoned_preprint, valid_preprint, valid_preprint_node,
            no_preprints_node, url_base):
        expected_ids = [
            abandoned_preprint_node._id,
            no_preprints_node._id]
        res = app.get('{}false'.format(url_base), auth=user.auth)
        actual_ids = [n['id'] for n in res.json['data']]

        assert set(expected_ids) == set(actual_ids)

    def test_filter_true(
            self, app, user, valid_preprint_node, abandoned_preprint_node, abandoned_preprint,
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

@pytest.mark.django_db
class TestNodeListPermissionFiltering:

    @pytest.fixture()
    def creator(self):
        return UserFactory()

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def no_perm_node(self, creator):
        return ProjectFactory(creator=creator)

    @pytest.fixture()
    def read_node(self, creator, contrib):
        node = ProjectFactory(creator=creator)
        node.add_contributor(contrib, permissions=permissions.READ, save=True)
        return node

    @pytest.fixture()
    def write_node(self, creator, contrib):
        node = ProjectFactory(creator=creator)
        node.add_contributor(contrib, permissions=permissions.WRITE, save=True)
        return node

    @pytest.fixture()
    def admin_node(self, creator, contrib):
        node = ProjectFactory(creator=creator)
        node.add_contributor(contrib, permissions=permissions.ADMIN, save=True)
        return node

    @pytest.fixture()
    def url(self):
        return '/{}users/me/nodes/?filter[current_user_permissions]='.format(API_BASE)

    def test_current_user_permissions_filter(self, app, url, contrib, no_perm_node, read_node, write_node, admin_node):
        # test filter read
        res = app.get('{}read'.format(url), auth=contrib.auth)
        assert len(res.json['data']) == 3
        assert set([read_node._id, write_node._id, admin_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter write
        res = app.get('{}write'.format(url), auth=contrib.auth)
        assert len(res.json['data']) == 2
        assert set([admin_node._id, write_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter admin
        res = app.get('{}admin'.format(url), auth=contrib.auth)
        assert len(res.json['data']) == 1
        assert [admin_node._id] == [node['id'] for node in res.json['data']]

        # test filter null
        res = app.get('{}null'.format(url), auth=contrib.auth, expect_errors=True)
        assert res.status_code == 400

        user2 = AuthUserFactory()
        osf_group = OSFGroupFactory(creator=user2)
        read_node.add_osf_group(osf_group, permissions.READ)
        write_node.add_osf_group(osf_group, permissions.WRITE)
        admin_node.add_osf_group(osf_group, permissions.ADMIN)

        # test filter group member read
        res = app.get('{}read'.format(url), auth=user2.auth)
        assert len(res.json['data']) == 3
        assert set([read_node._id, write_node._id, admin_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter group member write
        res = app.get('{}write'.format(url), auth=user2.auth)
        assert len(res.json['data']) == 2
        assert set([admin_node._id, write_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter group member admin
        res = app.get('{}admin'.format(url), auth=user2.auth)
        assert len(res.json['data']) == 1
        assert [admin_node._id] == [node['id'] for node in res.json['data']]

    def test_filter_my_current_user_permissions_to_other_users_nodes(self, app, contrib, no_perm_node, read_node, write_node, admin_node):
        url = '/{}users/{}/nodes/?filter[current_user_permissions]='.format(API_BASE, contrib._id)

        me = AuthUserFactory()

        # test filter read
        res = app.get('{}read'.format(url), auth=me.auth)
        assert len(res.json['data']) == 0

        read_node.add_contributor(me, permissions.READ)
        read_node.save()
        res = app.get('{}read'.format(url), auth=me.auth)
        assert len(res.json['data']) == 1
        assert set([read_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter write
        res = app.get('{}write'.format(url), auth=me.auth)
        assert len(res.json['data']) == 0
        write_node.add_contributor(me, permissions.WRITE)
        write_node.save()
        res = app.get('{}write'.format(url), auth=me.auth)
        assert len(res.json['data']) == 1
        assert set([write_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter admin
        res = app.get('{}admin'.format(url), auth=me.auth)
        assert len(res.json['data']) == 0

        res = app.get('{}admin'.format(url), auth=me.auth)
        admin_node.add_contributor(me, permissions.ADMIN)
        admin_node.save()
        res = app.get('{}admin'.format(url), auth=me.auth)
        assert len(res.json['data']) == 1
        assert set([admin_node._id]) == set([node['id'] for node in res.json['data']])
        res = app.get('{}read'.format(url), auth=me.auth)
        assert len(res.json['data']) == 3
        assert set([read_node._id, write_node._id, admin_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter nonauthenticated_user v2.11
        read_node.is_public = True
        read_node.save()
        res = app.get('{}read&version=2.11'.format(url))
        assert len(res.json['data']) == 0

        # test filter nonauthenticated_user v2.2
        res = app.get('{}read&version=2.2'.format(url))
        assert len(res.json['data']) == 1
        assert set([read_node._id]) == set([node['id'] for node in res.json['data']])

        # test filter nonauthenticated_user v2.2
        res = app.get('{}write&version=2.2'.format(url))
        assert len(res.json['data']) == 0

        # test filter nonauthenticated_user v2.2
        res = app.get('{}admin&version=2.2'.format(url))
        assert len(res.json['data']) == 0
