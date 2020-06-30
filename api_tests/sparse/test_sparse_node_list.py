import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import AbstractNode
from osf.utils import permissions
from osf_tests.factories import (
    CollectionFactory,
    ProjectFactory,
    AuthUserFactory,
    PreprintFactory,
    InstitutionFactory,
    OSFGroupFactory,
    DraftNodeFactory,
)
from website.views import find_bookmark_collection


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def non_contrib():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeList:

    @pytest.fixture()
    def deleted_project(self):
        return ProjectFactory(is_deleted=True)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def sparse_url(self, user):
        return '/{}sparse/nodes/'.format(API_BASE)

    @pytest.fixture()
    def preprint(self, public_project, user):
        preprint = PreprintFactory(creator=user, finish=True)
        preprint.node = public_project
        preprint.save()
        return preprint

    @pytest.fixture()
    def draft_node(self, user):
        return DraftNodeFactory(creator=user)

    def test_return(
            self, app, user, non_contrib, deleted_project, draft_node,
            private_project, public_project, sparse_url):

        #   test_only_returns_non_deleted_public_projects
        res = app.get(sparse_url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project._id in ids
        assert deleted_project._id not in ids
        assert private_project._id not in ids
        assert draft_node._id not in ids

        #   test_return_public_node_list_logged_out_user
        res = app.get(sparse_url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids
        assert draft_node._id not in ids

        #   test_return_public_node_list_logged_in_user
        res = app.get(sparse_url, auth=non_contrib)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids
        assert draft_node._id not in ids

        #   test_return_private_node_list_logged_out_user
        res = app.get(sparse_url)
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids
        assert draft_node._id not in ids

        #   test_return_private_node_list_logged_in_contributor
        res = app.get(sparse_url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id in ids
        assert draft_node._id not in ids

        #   test_return_private_node_list_logged_in_non_contributor
        res = app.get(sparse_url, auth=non_contrib.auth)
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids
        assert draft_node._id not in ids

        #   test_returns_nodes_through_which_you_have_perms_through_osf_groups
        group = OSFGroupFactory(creator=user)
        another_project = ProjectFactory()
        another_project.add_osf_group(group, permissions.READ)
        res = app.get(sparse_url, auth=user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert another_project._id in ids

    def test_node_list_has_proper_root(self, app, user, sparse_url):
        project_one = ProjectFactory(title='Project One', is_public=True)
        ProjectFactory(parent=project_one, is_public=True)

        res = app.get(sparse_url + '?embed=root&embed=parent', auth=user.auth)

        for project_json in res.json['data']:
            project = AbstractNode.load(project_json['id'])
            assert project_json['embeds']['root']['data']['id'] == project.root._id

    def test_node_list_sorting(self, app, sparse_url):
        res = app.get(f'{sparse_url}?sort=-created')
        assert res.status_code == 200

        res = app.get(f'{sparse_url}?sort=title')
        assert res.status_code == 200


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_bookmark_creation
class TestNodeFiltering:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def tag_one(self):
        return 'tag_one'

    @pytest.fixture()
    def tag_two(self):
        return 'tag_two'

    @pytest.fixture()
    def public_project_one(self, tag_one, tag_two):
        public_project_one = ProjectFactory(
            title='Public Project One',
            description='One',
            is_public=True)
        public_project_one.add_tag(
            tag_one,
            Auth(public_project_one.creator),
            save=False)
        public_project_one.add_tag(
            tag_two,
            Auth(public_project_one.creator),
            save=False)
        public_project_one.save()
        return public_project_one

    @pytest.fixture()
    def public_project_two(self, tag_one):
        public_project_two = ProjectFactory(
            title='Public Project Two',
            description='One or Two',
            is_public=True)
        public_project_two.add_tag(
            tag_one,
            Auth(public_project_two.creator),
            save=True)
        return public_project_two

    @pytest.fixture()
    def public_project_three(self):
        return ProjectFactory(title='Unique Test Title', description='three', is_public=True)

    @pytest.fixture()
    def user_one_private_project(self, user_one):
        return ProjectFactory(
            title='User One Private Project',
            is_public=False,
            creator=user_one)

    @pytest.fixture()
    def user_two_private_project(self, user_two):
        return ProjectFactory(
            title='User Two Private Project',
            is_public=False,
            creator=user_two)

    @pytest.fixture()
    def preprint(self, user_one):
        return PreprintFactory(project=ProjectFactory(creator=user_one), creator=user_one)

    @pytest.fixture()
    def folder(self):
        return CollectionFactory()

    @pytest.fixture()
    def bookmark_collection(self, user_one):
        return find_bookmark_collection(user_one)

    @pytest.fixture()
    def sparse_url(self):
        return f'/{API_BASE}sparse/nodes/'

    def test_filtering(
            self, app, user_one, public_project_one,
            public_project_two, public_project_three,
            user_one_private_project, user_two_private_project,
            preprint, sparse_url):

        #   test_filtering_by_id
        filter_url = f'{sparse_url}?filter[id]={public_project_one._id}'
        res = app.get(filter_url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert len(ids) == 1

        #   test_filtering_by_multiple_ids
        filter_url = f'{sparse_url}?filter[id]={public_project_one._id},{public_project_two._id}'
        res = app.get(filter_url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert len(ids) == 2

        #   test_filtering_by_multiple_ids_one_private
        filter_url = f'{sparse_url}?filter[id]={public_project_one._id},{user_two_private_project._id}'
        res = app.get(filter_url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert user_two_private_project._id not in ids
        assert len(ids) == 1

        #   test_filtering_by_multiple_ids_brackets_in_query_params
        filter_url = f'{sparse_url}?filter[id]=[{public_project_one._id},   {public_project_two._id}]'
        res = app.get(filter_url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert len(ids) == 2

        #   test_filtering_on_title_not_equal
        filter_url = f'{sparse_url}?filter[title][ne]=Public%20Project%20One'
        res = app.get(filter_url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 4

        titles = [each['attributes']['title'] for each in data]

        assert public_project_one.title not in titles
        assert public_project_two.title in titles
        assert public_project_three.title in titles
        assert user_one_private_project.title in titles

        #   test_filtering_on_description_not_equal
        filter_url = f'{sparse_url}?filter[description][ne]=reason%20is%20shook'
        res = app.get(filter_url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 5

        descriptions = [each['attributes']['description'] for each in data]

        assert public_project_one.description in descriptions
        assert public_project_three.description in descriptions
        assert user_one_private_project.description in descriptions


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestNodeCreate:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self, institution):
        auth_user = AuthUserFactory()
        auth_user.affiliated_institutions.add(institution)
        return auth_user

    @pytest.fixture()
    def sparse_url(self):
        return f'/{API_BASE}sparse/nodes/'

    @pytest.fixture()
    def public_project_payload(self, institution):
        return {
            'data': {
                'type': 'sparse-nodes',
                'attributes': {
                    'title': 'Rheisen is bored',
                    'description': 'Pytest conversions are tedious',
                    'category': 'data',
                    'public': True,
                },
                'relationships': {
                    'affiliated_institutions': {
                        'data': [
                            {
                                'type': 'institutions',
                                'id': institution._id,
                            }
                        ]
                    }
                },
            }
        }

    def test_create_node_errors(self, app, user, public_project_payload, sparse_url):
        res = app.post_json_api(sparse_url, public_project_payload, expect_errors=True, auth=user.auth)
        assert res.status_code == 405
