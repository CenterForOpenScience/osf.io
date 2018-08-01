import pytest

from api.base.settings.defaults import API_BASE, MAX_PAGE_SIZE
from api_tests.nodes.filters.test_filters import NodesListFilteringMixin, NodesListDateFilteringMixin
from framework.auth.core import Auth
from osf.models import AbstractNode, Node, NodeLog
from osf.utils.sanitize import strip_html
from osf.utils import permissions
from osf_tests.factories import (
    CollectionFactory,
    ProjectFactory,
    NodeFactory,
    RegistrationFactory,
    AuthUserFactory,
    UserFactory,
    PreprintFactory,
    InstitutionFactory,
    RegionFactory
)
from addons.osfstorage.settings import DEFAULT_REGION_ID
from rest_framework import exceptions
from tests.utils import assert_items_equal
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
    def url(self, user):
        return '/{}nodes/'.format(API_BASE)

    def test_return(
            self, app, user, non_contrib, deleted_project,
            private_project, public_project, url):

        #   test_only_returns_non_deleted_public_projects
        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project._id in ids
        assert deleted_project._id not in ids
        assert private_project._id not in ids

    #   test_return_public_node_list_logged_out_user
        res = app.get(url, expect_errors=True)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids

    #   test_return_public_node_list_logged_in_user
        res = app.get(url, auth=non_contrib)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids

    #   test_return_private_node_list_logged_out_user
        res = app.get(url)
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids

    #   test_return_private_node_list_logged_in_contributor
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id in ids

    #   test_return_private_node_list_logged_in_non_contributor
        res = app.get(url, auth=non_contrib.auth)
        ids = [each['id'] for each in res.json['data']]
        assert public_project._id in ids
        assert private_project._id not in ids

    def test_node_list_does_not_returns_registrations(
            self, app, user, public_project, url):
        registration = RegistrationFactory(
            project=public_project, creator=user)
        res = app.get(url, auth=user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert registration._id not in ids

    def test_node_list_has_root(
            self, app, user, url, public_project, private_project,
            deleted_project):
        res = app.get(url, auth=user.auth)
        projects_with_root = 0
        for project in res.json['data']:
            if project['relationships'].get('root', None):
                projects_with_root += 1
        assert projects_with_root != 0
        assert all(
            [each['relationships'].get(
                'root'
            ) is not None for each in res.json['data']]
        )

    def test_node_list_has_proper_root(self, app, user, url):
        project_one = ProjectFactory(title='Project One', is_public=True)
        ProjectFactory(parent=project_one, is_public=True)

        res = app.get(url + '?embed=root&embed=parent', auth=user.auth)

        for project_json in res.json['data']:
            project = AbstractNode.load(project_json['id'])
            assert project_json['embeds']['root']['data']['id'] == project.root._id

    def test_node_list_sorting(self, app, url):
        res = app.get('{}?sort=-created'.format(url))
        assert res.status_code == 200

        res = app.get('{}?sort=title'.format(url))
        assert res.status_code == 200

    def test_node_list_embed_region(self, app, url, public_project):
        res = app.get('{}?embed=region'.format(url))
        assert res.status_code == 200
        assert res.json['data'][0]['embeds']['region']['data']['id'] == DEFAULT_REGION_ID


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
        return PreprintFactory(creator=user_one)

    @pytest.fixture()
    def folder(self):
        return CollectionFactory()

    @pytest.fixture()
    def bookmark_collection(self, user_one):
        return find_bookmark_collection(user_one)

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    def test_filtering(
            self, app, user_one, public_project_one,
            public_project_two, public_project_three,
            user_one_private_project, user_two_private_project,
            preprint):

        #   test_filtering_by_id
        url = '/{}nodes/?filter[id]={}'.format(
            API_BASE, public_project_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert len(ids) == 1

    #   test_filtering_by_multiple_ids
        url = '/{}nodes/?filter[id]={},{}'.format(
            API_BASE, public_project_one._id, public_project_two._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert len(ids) == 2

    #   test_filtering_by_multiple_ids_one_private
        url = '/{}nodes/?filter[id]={},{}'.format(
            API_BASE, public_project_one._id, user_two_private_project._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert user_two_private_project._id not in ids
        assert len(ids) == 1

    #   test_filtering_by_multiple_ids_brackets_in_query_params
        url = '/{}nodes/?filter[id]=[{},   {}]'.format(
            API_BASE, public_project_one._id, public_project_two._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        ids = [each['id'] for each in res.json['data']]

        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert len(ids) == 2

    #   test_filtering_on_title_not_equal
        url = '/{}nodes/?filter[title][ne]=Public%20Project%20One'.format(
            API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 4

        titles = [each['attributes']['title'] for each in data]

        assert public_project_one.title not in titles
        assert public_project_two.title in titles
        assert public_project_three.title in titles
        assert user_one_private_project.title in titles

    #   test_filtering_on_description_not_equal
        url = '/{}nodes/?filter[description][ne]=reason%20is%20shook'.format(
            API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 5

        descriptions = [each['attributes']['description'] for each in data]

        assert public_project_one.description in descriptions
        assert public_project_three.description in descriptions
        assert user_one_private_project.description in descriptions

    #   test_filtering_on_preprint
        url = '/{}nodes/?filter[preprint]=true'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        ids = [each['id'] for each in data]

        preprints = Node.objects.filter(
            preprint_file__isnull=False
        ).exclude(_is_preprint_orphan=True)
        assert len(data) == len(preprints)
        assert preprint.node._id in ids
        assert public_project_one._id not in ids
        assert public_project_two._id not in ids
        assert public_project_three._id not in ids

    #   test_filtering_out_preprint
        url = '/{}nodes/?filter[preprint]=false'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']

        ids = [each['id'] for each in data]

        assert preprint.node._id not in ids
        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert public_project_three._id in ids

    def test_filtering_by_category(self, app, user_one):
        project_one = ProjectFactory(creator=user_one, category='hypothesis')
        project_two = ProjectFactory(creator=user_one, category='procedure')
        url = '/{}nodes/?filter[category]=hypothesis'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)

        node_json = res.json['data']
        ids = [each['id'] for each in node_json]

        assert project_one._id in ids
        assert project_two._id not in ids

    def test_filtering_by_public(self, app, user_one):
        public_project = ProjectFactory(creator=user_one, is_public=True)
        private_project = ProjectFactory(creator=user_one, is_public=False)

        url = '/{}nodes/?filter[public]=false'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        # No public projects returned
        assert not any([each['attributes']['public'] for each in node_json])

        ids = [each['id'] for each in node_json]
        assert public_project._id not in ids
        assert private_project._id in ids

        url = '/{}nodes/?filter[public]=true'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        # No private projects returned
        assert all([each['attributes']['public'] for each in node_json])

        ids = [each['id'] for each in node_json]
        assert private_project._id not in ids
        assert public_project._id in ids

    def test_filtering_by_public_toplevel(self, app, user_one):
        public_project = ProjectFactory(creator=user_one, is_public=True)
        private_project = ProjectFactory(creator=user_one, is_public=False)

        url = '/{}nodes/?filter[public]=false&filter[parent]=null'.format(
            API_BASE)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        # No public projects returned
        assert not any([each['attributes']['public'] for each in node_json])

        ids = [each['id'] for each in node_json]
        assert public_project._id not in ids
        assert private_project._id in ids

        url = '/{}nodes/?filter[public]=true&filter[parent]=null'.format(
            API_BASE)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        # No private projects returned
        assert all([each['attributes']['public'] for each in node_json])

        ids = [each['id'] for each in node_json]
        assert private_project._id not in ids
        assert public_project._id in ids

    def test_filtering_tags(
            self, app, public_project_one, public_project_two,
            tag_one, tag_two):
        url = '/{}nodes/?filter[tags]={}'.format(API_BASE, tag_one)

        res = app.get(url, auth=public_project_one.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id in ids

    #   test_filter_two_tags
        url = '/{}nodes/?filter[tags]={}&filter[tags]={}'.format(
            API_BASE, tag_one, tag_two)

        res = app.get(url, auth=public_project_one.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id not in ids

    #   test_filter_no_tags
        project_no_tag = ProjectFactory(
            title='Project No Tags', is_public=True)

        url = '/{}nodes/?filter[tags]=null'.format(API_BASE)

        res = app.get(url, auth=project_no_tag.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id not in ids
        assert public_project_two._id not in ids
        assert project_no_tag._id in ids

    def test_filtering_multiple_fields(self, app, user_one):
        project_public_one = ProjectFactory(
            is_public=True, title='test', creator=user_one)
        project_private_one = ProjectFactory(
            is_public=False, title='test', creator=user_one)
        project_public_two = ProjectFactory(
            is_public=True,
            title='kitten',
            creator=user_one,
            description='test')
        project_private_two = ProjectFactory(
            is_public=False, title='kitten', creator=user_one)
        project_public_three = ProjectFactory(
            is_public=True, title='test', creator=user_one)
        project_public_four = ProjectFactory(
            is_public=True,
            title='test',
            creator=user_one,
            description='test')

        for project in [
                project_public_one, project_public_two,
                project_public_three, project_private_one,
                project_private_two]:
            project.created = '2016-10-25 00:00:00.000000+00:00'
            project.save()

        project_public_four.created = '2016-10-28 00:00:00.000000+00:00'
        project_public_four.save()

        expected = [
            project_public_one._id,
            project_public_two._id,
            project_public_three._id]
        url = '/{}nodes/?filter[public]=true&filter[title,description]=test&filter[date_created]=2016-10-25'.format(
            API_BASE)
        res = app.get(url, auth=user_one.auth)
        actual = [node['id'] for node in res.json['data']]

        assert len(expected) == len(actual)
        assert set(expected) == set(actual)

    def test_filtering_tags_exact(
            self, app, user_one,
            public_project_one,
            public_project_two):
        public_project_one.add_tag('logic', Auth(user_one))
        public_project_two.add_tag('logic', Auth(user_one))
        public_project_one.add_tag('reason', Auth(user_one))
        res = app.get(
            '/{}nodes/?filter[tags]=reason'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_tags_capitalized_query(
            self, app, user_one, public_project_one):
        public_project_one.add_tag('covfefe', Auth(user_one))
        res = app.get(
            '/{}nodes/?filter[tags]=COVFEFE'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_tags_capitalized_tag(
            self, app, user_one, public_project_one):
        public_project_one.add_tag('COVFEFE', Auth(user_one))
        res = app.get(
            '/{}nodes/?filter[tags]=covfefe'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_on_multiple_tags(
            self, app, user_one, public_project_one):
        public_project_one.add_tag('lovechild', Auth(user_one))
        public_project_one.add_tag('flowerchild', Auth(user_one))
        res = app.get(
            '/{}nodes/?filter[tags]=lovechild&filter[tags]=flowerchild'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_on_multiple_tags_must_match_both(
            self, app, user_one, public_project_one):
        public_project_one.add_tag('lovechild', Auth(user_one))
        res = app.get(
            '/{}nodes/?filter[tags]=lovechild&filter[tags]=flowerchild'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 0

    def test_filtering_tags_returns_distinct(
            self, app, user_one, public_project_one):
        # regression test for returning multiple of the same file
        public_project_one.add_tag('cat', Auth(user_one))
        public_project_one.add_tag('cAt', Auth(user_one))
        public_project_one.add_tag('caT', Auth(user_one))
        public_project_one.add_tag('CAT', Auth(user_one))
        res = app.get(
            '/{}nodes/?filter[tags]=cat'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_contributors(
            self, app, user_one, user_one_private_project,
            preprint):
        res = app.get(
            '/{}nodes/?filter[contributors]={}'.format(
                API_BASE, user_one._id
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 2

    def test_filtering_contributors_bad_id(self, app, user_one):
        res = app.get(
            '/{}nodes/?filter[contributors]=alovechilddresseduplikeaflowerchild'.format(
                API_BASE
            ),
            auth=user_one.auth
        )
        assert len(res.json.get('data')) == 0

    def test_get_projects(
            self, app, user_one, public_project_one,
            public_project_two, public_project_three,
            user_one_private_project, user_two_private_project,
            folder, bookmark_collection, url):

        #   test_get_all_projects_with_no_filter_logged_in
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert public_project_three._id in ids
        assert user_one_private_project._id in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_all_projects_with_no_filter_not_logged_in
        res = app.get(url)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert public_project_three._id in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_one_project_with_exact_filter_logged_in
        url = '/{}nodes/?filter[title]=Project%20One'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id not in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_one_project_with_exact_filter_not_logged_in
        url = '/{}nodes/?filter[title]=Project%20One'.format(API_BASE)

        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id not in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_some_projects_with_substring_logged_in
        url = '/{}nodes/?filter[title]=Two'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id not in ids
        assert public_project_two._id in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_some_projects_with_substring_not_logged_in
        url = '/{}nodes/?filter[title]=Two'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id not in ids
        assert public_project_two._id in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_only_public_or_my_projects_with_filter_logged_in
        url = '/{}nodes/?filter[title]=Project'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_get_only_public_projects_with_filter_not_logged_in
        url = '/{}nodes/?filter[title]=Project'.format(API_BASE)

        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert public_project_two._id in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_alternate_filtering_field_logged_in
        url = '/{}nodes/?filter[description]=One%20or%20Two'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id not in ids
        assert public_project_two._id in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    #   test_alternate_filtering_field_not_logged_in
        url = '/{}nodes/?filter[description]=reason'.format(API_BASE)

        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id not in ids
        assert public_project_three._id not in ids
        assert user_one_private_project._id not in ids
        assert user_two_private_project._id not in ids
        assert folder._id not in ids
        assert bookmark_collection._id not in ids

    def test_incorrect_filtering_field_not_logged_in(self, app):
        url = '/{}nodes/?filter[notafield]=bogus'.format(API_BASE)

        res = app.get(url, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == '\'notafield\' is not a valid field for this endpoint.'

    def test_filtering_on_root(self, app, user_one):
        root = ProjectFactory(is_public=True)
        child = ProjectFactory(parent=root, is_public=True)
        ProjectFactory(parent=root, is_public=True)
        ProjectFactory(parent=child, is_public=True)
        # create some unrelated projects
        ProjectFactory(
            title='A theory on why reason has a ridiculously large project',
            is_public=True)
        ProjectFactory(
            title='How one intern changed thousands of lines within a codebase',
            is_public=True)

        url = '/{}nodes/?filter[root]={}'.format(API_BASE, root._id)

        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

        root_nodes = AbstractNode.objects.filter(root__guids___id=root._id)

        assert len(res.json['data']) == root_nodes.count()

    def test_filtering_on_parent(self, app):
        root = ProjectFactory(is_public=True)
        parent_one = NodeFactory(parent=root, is_public=True)
        parent_two = NodeFactory(is_public=True, parent=root)
        child_one = NodeFactory(parent=parent_one, is_public=True)
        child_two = NodeFactory(parent=parent_one, is_public=True)

        url = '/{}nodes/?filter[parent]={}'.format(API_BASE, parent_one._id)
        res = app.get(url)
        assert res.status_code == 200

        guids = [each['id'] for each in res.json['data']]
        assert child_one._id in guids
        assert child_two._id in guids
        assert parent_one._id not in guids
        assert parent_two._id not in guids

    def test_filtering_on_null_parent(self, app):
        # add some nodes TO be included
        new_user = AuthUserFactory()
        root = ProjectFactory(is_public=True)
        root_two = ProjectFactory(is_public=True)
        # Build up a some of nodes not to be included
        child_one = ProjectFactory(parent=root, is_public=True)
        child_two = ProjectFactory(parent=root, is_public=True)
        grandchild = ProjectFactory(parent=child_one, is_public=True)

        url = '/{}nodes/?filter[parent]=null'.format(API_BASE)

        res = app.get(url, auth=new_user.auth)
        assert res.status_code == 200

        public_root_nodes = Node.objects.filter(is_public=True).get_roots()
        assert len(res.json['data']) == public_root_nodes.count()

        guids = [each['id'] for each in res.json['data']]
        assert root._id in guids
        assert root_two._id in guids
        assert child_one._id not in guids
        assert child_two._id not in guids
        assert grandchild._id not in guids

    def test_preprint_filter_excludes_orphans(
            self, app, user_one, preprint, public_project_one,
            public_project_two, public_project_three):
        orphan = PreprintFactory(creator=preprint.node.creator)
        orphan._is_preprint_orphan = True
        orphan.save()

        url = '/{}nodes/?filter[preprint]=true'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']

        ids = [each['id'] for each in data]

        assert preprint.node._id in ids
        assert orphan._id not in ids
        assert public_project_one._id not in ids
        assert public_project_two._id not in ids
        assert public_project_three._id not in ids

    def test_deleted_preprint_file_not_in_filtered_results(
            self, app, user_one, preprint):
        orphan = PreprintFactory(creator=preprint.node.creator)

        # orphan the preprint by deleting the file
        orphan.node.preprint_file = None
        orphan.node.save()
        url = '/{}nodes/?filter[preprint]=true'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']

        ids = [each['id'] for each in data]

        assert preprint.node._id in ids
        assert orphan.node._id not in ids

    def test_deleted_preprint_file_in_preprint_false_filtered_results(
            self, app, user_one, preprint):
        orphan = PreprintFactory(creator=preprint.node.creator)

        # orphan the preprint by deleting the file
        orphan.node.preprint_file = None
        orphan.node.save()
        orphan.refresh_from_db()

        url = '/{}nodes/?filter[preprint]=false'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']

        ids = [each['id'] for each in data]

        assert preprint.node._id not in ids
        assert orphan.node._id in ids

    def test_unpublished_preprint_not_in_preprint_true_filter_results(
            self, app, user_one, preprint):
        unpublished = PreprintFactory(
            creator=preprint.node.creator,
            is_published=False)
        assert not unpublished.is_published

        url = '/{}nodes/?filter[preprint]=true'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        ids = [each['id'] for each in data]

        assert preprint.node._id in ids
        assert unpublished.node._id not in ids

    def test_unpublished_preprint_in_preprint_false_filter_results(
            self, app, user_one, preprint):
        unpublished = PreprintFactory(
            creator=preprint.node.creator,
            is_published=False)
        assert not unpublished.is_published

        url = '/{}nodes/?filter[preprint]=false'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        ids = [each['id'] for each in data]

        assert preprint.node._id not in ids
        assert unpublished.node._id in ids

    def test_nodes_list_filter_multiple_field(
            self, app, public_project_one, public_project_two,
            public_project_three, user_one):

        url = '/{}nodes/?filter[title,description]=One'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project_one._id in ids
        assert 'One' in public_project_one.title

        assert public_project_two._id in ids
        assert 'One' in public_project_two.description
        assert public_project_three._id not in ids


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestNodeCreate:

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_one(self, institution_one):
        auth_user = AuthUserFactory()
        auth_user.affiliated_institutions.add(institution_one)
        return auth_user

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def title(self):
        return 'Rheisen is bored'

    @pytest.fixture()
    def description(self):
        return 'Pytest conversions are tedious'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def region(self):
        return RegionFactory(name='Frankfort', _id='eu-central-1')

    @pytest.fixture()
    def url_with_region_query_param(self, region, url):
        return url + '?region={}'.format(region._id)

    @pytest.fixture()
    def public_project(self, title, description, category, institution_one):
        return {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': True,
                },
                'relationships': {
                    'affiliated_institutions': {
                        'data': [
                            {
                                'type': 'institutions',
                                'id': institution_one._id,
                            }
                        ]
                    }
                },
            }
        }

    @pytest.fixture()
    def private_project(self, title, description, category):
        return {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': False
                }
            }
        }

    def test_create_node_errors(
            self, app, user_one, public_project,
            private_project, url):

        #   test_node_create_invalid_data
        res = app.post_json_api(
            url, 'Incorrect data',
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

        res = app.post_json_api(
            url, ['Incorrect data'],
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_creates_public_project_logged_out
        res = app.post_json_api(url, public_project, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_creates_private_project_logged_out
        res = app.post_json_api(url, private_project, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_creates_public_project_logged_in(
            self, app, user_one, public_project, url, institution_one):
        res = app.post_json_api(
            url, public_project,
            expect_errors=True,
            auth=user_one.auth)
        assert res.status_code == 201
        self_link = res.json['data']['links']['self']
        assert res.json['data']['attributes']['title'] == public_project['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == public_project['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == public_project['data']['attributes']['category']
        assert res.json['data']['relationships']['affiliated_institutions']['links']['self']['href'] ==  \
               '{}relationships/institutions/'.format(self_link)
        assert res.content_type == 'application/vnd.api+json'
        pid = res.json['data']['id']
        project = AbstractNode.load(pid)
        assert project.logs.latest().action == NodeLog.AFFILIATED_INSTITUTION_ADDED
        assert institution_one in project.affiliated_institutions.all()

    def test_creates_private_project_logged_in_contributor(
            self, app, user_one, private_project, url):
        res = app.post_json_api(url, private_project, auth=user_one.auth)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == private_project['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == private_project['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == private_project['data']['attributes']['category']
        pid = res.json['data']['id']
        project = AbstractNode.load(pid)
        assert project.logs.latest().action == NodeLog.PROJECT_CREATED

    def test_create_from_template_errors(self, app, user_one, user_two, url):

        #   test_404_on_create_from_template_of_nonexistent_project
        template_from_id = 'thisisnotavalidguid'
        templated_project_data = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': 'No title',
                        'category': 'project',
                        'template_from': template_from_id,
                    }
            }
        }
        res = app.post_json_api(
            url, templated_project_data,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404

    #   test_403_on_create_from_template_of_unauthorized_project
        template_from = ProjectFactory(creator=user_two, is_public=True)
        templated_project_data = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': 'No permission',
                        'category': 'project',
                        'template_from': template_from._id,
                    }
            }
        }
        res = app.post_json_api(
            url, templated_project_data,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_creates_project_from_template(self, app, user_one, category, url):
        template_from = ProjectFactory(creator=user_one, is_public=True)
        template_component = ProjectFactory(
            creator=user_one, is_public=True, parent=template_from)
        templated_project_title = 'Templated Project'
        templated_project_data = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': templated_project_title,
                        'category': category,
                        'template_from': template_from._id,
                    }
            }
        }

        res = app.post_json_api(
            url, templated_project_data,
            auth=user_one.auth)
        assert res.status_code == 201
        json_data = res.json['data']

        new_project_id = json_data['id']
        new_project = AbstractNode.load(new_project_id)
        assert new_project.title == templated_project_title
        assert new_project.description == ''
        assert not new_project.is_public
        assert len(new_project.nodes) == len(template_from.nodes)
        assert new_project.nodes[0].title == template_component.title

    def test_creates_project_creates_project_and_sanitizes_html(
            self, app, user_one, category, url):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> project'

        res = app.post_json_api(url, {
            'data': {
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': True
                },
                'type': 'nodes'
            }
        }, auth=user_one.auth)
        project_id = res.json['data']['id']
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        url = '/{}nodes/{}/'.format(API_BASE, project_id)

        project = AbstractNode.load(project_id)
        assert project.logs.latest().action == NodeLog.PROJECT_CREATED

        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == strip_html(title)
        assert res.json['data']['attributes']['description'] == strip_html(
            description)
        assert res.json['data']['attributes']['category'] == category

    def test_create_component_inherit_contributors(
            self, app, user_one, user_two, title, category):
        parent_project = ProjectFactory(creator=user_one)
        parent_project.add_contributor(
            user_two, permissions=[permissions.READ], save=True)
        url = '/{}nodes/{}/children/?inherit_contributors=true'.format(
            API_BASE, parent_project._id)
        component_data = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'category': category,
                }
            }
        }
        res = app.post_json_api(url, component_data, auth=user_one.auth)
        assert res.status_code == 201
        json_data = res.json['data']

        new_component_id = json_data['id']
        new_component = AbstractNode.load(new_component_id)
        assert len(new_component.contributors) == 2
        assert len(
            new_component.contributors
        ) == len(parent_project.contributors)

    def test_create_component_with_tags(self, app, user_one, title, category):
        parent_project = ProjectFactory(creator=user_one)
        url = '/{}nodes/{}/children/'.format(API_BASE, parent_project._id)
        component_data = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'category': category,
                    'tags': ['test tag 1', 'test tag 2']
                }
            }
        }
        res = app.post_json_api(url, component_data, auth=user_one.auth)
        assert res.status_code == 201
        json_data = res.json['data']

        new_component_id = json_data['id']
        new_component = AbstractNode.load(new_component_id)

        assert len(new_component.tags.all()) == 2
        tag1, tag2 = new_component.tags.all()
        assert tag1.name == 'test tag 1'
        assert tag2.name == 'test tag 2'

    def test_create_component_inherit_contributors_with_unregistered_contributor(
            self, app, user_one, title, category):
        parent_project = ProjectFactory(creator=user_one)
        parent_project.add_unregistered_contributor(
            fullname='far', email='foo@bar.baz',
            permissions=[permissions.READ],
            auth=Auth(user=user_one), save=True)
        url = '/{}nodes/{}/children/?inherit_contributors=true'.format(
            API_BASE, parent_project._id)
        component_data = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'category': category,
                }
            }
        }
        res = app.post_json_api(url, component_data, auth=user_one.auth)
        assert res.status_code == 201
        json_data = res.json['data']

        new_component_id = json_data['id']
        new_component = AbstractNode.load(new_component_id)
        assert len(new_component.contributors) == 2
        assert len(
            new_component.contributors
        ) == len(parent_project.contributors)

    def test_create_project_with_region_relationship(
            self, app, user_one, region, private_project, url):
        private_project['data']['relationships'] = {
            'region': {
                'data': {
                    'type': 'region',
                    'id': region._id
                }
            }
        }
        res = app.post_json_api(
            url, private_project, auth=user_one.auth
        )
        assert res.status_code == 201
        region_id = res.json['data']['relationships']['region']['data']['id']
        assert region_id == region._id

    def test_create_project_with_region_query_param(
            self, app, user_one, region, private_project, url_with_region_query_param):
        res = app.post_json_api(
            url_with_region_query_param, private_project, auth=user_one.auth
        )
        assert res.status_code == 201
        pid = res.json['data']['id']
        project = AbstractNode.load(pid)

        node_settings = project.get_addon('osfstorage')
        assert node_settings.region_id == region.id

    def test_create_project_with_no_region_specified(self, app, user_one, private_project, url):
        res = app.post_json_api(
            url, private_project, auth=user_one.auth
        )
        assert res.status_code == 201
        project = AbstractNode.load(res.json['data']['id'])

        node_settings = project.get_addon('osfstorage')
        # NodeSettings just left at default region on creation
        assert node_settings.region_id == 1

    def test_create_project_with_bad_region_query_param(
            self, app, user_one, region, private_project, url):
        bad_region_id = 'bad-region-1'
        res = app.post_json_api(
            url + '?region={}'.format(bad_region_id), private_project,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Region {} is invalid.'.format(bad_region_id)

    def test_create_project_errors(
            self, app, user_one, title, description, category, url):

        #   test_creates_project_no_type
        project = {
            'data': {
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': False
                }
            }
        }
        res = app.post_json_api(
            url, project, auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_creates_project_incorrect_type
        project = {
            'data': {
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'public': False
                },
                'type': 'Wrong type.'
            }
        }
        res = app.post_json_api(
            url, project, auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "nodes", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'

    #   test_creates_project_properties_not_nested
        project = {
            'data': {
                'title': title,
                'description': description,
                'category': category,
                'public': False,
                'type': 'nodes'
            }
        }
        res = app.post_json_api(
            url, project, auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/attributes.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes'

    #   test_create_project_invalid_title
        project = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': 'A' * 201,
                    'description': description,
                    'category': category,
                    'public': False,
                }
            }
        }
        res = app.post_json_api(
            url, project, auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Title cannot exceed 200 characters.'


@pytest.mark.django_db
class TestNodeBulkCreate:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def title(self):
        return 'Rheisen is bored'

    @pytest.fixture()
    def description(self):
        return 'Pytest conversions are tedious'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def public_project(self, title, description, category):
        return {
            'type': 'nodes',
            'attributes': {
                'title': title,
                'description': description,
                'category': category,
                'public': True
            }
        }

    @pytest.fixture()
    def private_project(self, title, description, category):
        return {
            'type': 'nodes',
            'attributes': {
                'title': title,
                'description': description,
                'category': category,
                'public': False
            }
        }

    @pytest.fixture()
    def empty_project(self):
        return {
            'type': 'nodes',
            'attributes': {
                'title': '',
                'description': '',
                'category': ''
            }
        }

    def test_bulk_create(
            self, app, user_one, public_project, private_project,
            empty_project, title, category, url):

        #   test_bulk_create_nodes_blank_request
        res = app.post_json_api(
            url, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_create_all_or_nothing
        res = app.post_json_api(
            url,
            {'data': [public_project, empty_project]},
            bulk=True, auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_bulk_create_logged_out
        res = app.post_json_api(
            url,
            {'data': [public_project, private_project]},
            bulk=True, expect_errors=True)
        assert res.status_code == 401

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_bulk_create_error_formatting
        res = app.post_json_api(
            url,
            {'data': [empty_project, empty_project]},
            bulk=True, auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = res.json['errors']
        assert errors[0]['source'] == {'pointer': '/data/0/attributes/title'}
        assert errors[1]['source'] == {'pointer': '/data/1/attributes/title'}
        assert errors[0]['detail'] == 'This field may not be blank.'
        assert errors[1]['detail'] == 'This field may not be blank.'

    #   test_bulk_create_limits
        node_create_list = {'data': [public_project] * 101}
        res = app.post_json_api(
            url, node_create_list,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_bulk_create_no_type
        payload = {
            'data': [{
                'attributes': {
                    'category': category,
                    'title': title
                }
            }]
        }
        res = app.post_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/0/type'

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_bulk_create_incorrect_type
        payload = {
            'data': [
                public_project, {
                    'type': 'Incorrect type.',
                    'attributes': {
                        'category': category,
                        'title': title
                    }
                }
            ]
        }
        res = app.post_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_bulk_create_no_attributes
        payload = {'data': [public_project, {'type': 'nodes', }]}
        res = app.post_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes'

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_bulk_create_no_title
        payload = {
            'data': [
                public_project, {
                    'type': 'nodes',
                    'attributes': {
                        'category': category
                    }
                }
            ]
        }
        res = app.post_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/attributes/title'

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    #   test_ugly_payload
        payload = 'sdf;jlasfd'
        res = app.post_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 0

    def test_bulk_create_logged_in(
            self, app, user_one, public_project,
            private_project, url):
        res = app.post_json_api(
            url,
            {'data': [public_project, private_project]},
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 201
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['attributes']['title'] == public_project['attributes']['title']
        assert res.json['data'][0]['attributes']['category'] == public_project['attributes']['category']
        assert res.json['data'][0]['attributes']['description'] == public_project['attributes']['description']
        assert res.json['data'][1]['attributes']['title'] == private_project['attributes']['title']
        assert res.json['data'][1]['attributes']['category'] == public_project['attributes']['category']
        assert res.json['data'][1]['attributes']['description'] == public_project['attributes']['description']
        assert res.content_type == 'application/vnd.api+json'

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 2
        id_one = res.json['data'][0]['id']
        id_two = res.json['data'][1]['id']

        res = app.delete_json_api(
            url,
            {
                'data': [
                    {'id': id_one, 'type': 'nodes'},
                    {'id': id_two, 'type': 'nodes'}
                ]
            },
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 204


@pytest.mark.django_db
class TestNodeBulkUpdate:

    @pytest.fixture()
    def title(self):
        return 'Rheisen is bored'

    @pytest.fixture()
    def new_title(self):
        return 'Rheisen is very bored'

    @pytest.fixture()
    def description(self):
        return 'Pytest conversions are tedious'

    @pytest.fixture()
    def new_description(self):
        return 'Pytest conversions are death'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def new_category(self):
        return 'project'

    @pytest.fixture()
    def public_project_one(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user)

    @pytest.fixture()
    def public_project_two(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user)

    @pytest.fixture()
    def public_payload(
            self, public_project_one, public_project_two,
            new_title, new_description, new_category):
        return {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': True
                    }
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': True
                    }
                }
            ]
        }

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def private_project_one(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user)

    @pytest.fixture()
    def private_project_two(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user)

    @pytest.fixture()
    def private_payload(
            self, private_project_one, private_project_two,
            new_title, new_description, new_category):
        return {
            'data': [
                {
                    'id': private_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': False
                    }
                },
                {
                    'id': private_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': False
                    }
                }
            ]
        }

    @pytest.fixture()
    def empty_payload(self, public_project_one, public_project_two):
        return {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': '',
                        'description': '',
                        'category': ''
                    }
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': '',
                        'description': '',
                        'category': ''
                    }
                }
            ]
        }

    def test_bulk_update_errors(
            self, app, user, public_project_one,
            public_project_two, private_project_one,
            private_project_two, public_payload,
            private_payload, empty_payload, title,
            new_title, new_category, url):

        #   test_bulk_update_nodes_blank_request
        res = app.put_json_api(
            url, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_update_blank_but_not_empty_title
        payload = {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': 'This shouldn\'t update.',
                        'category': 'instrumentation'
                    }
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': '',
                        'category': 'hypothesis'
                    }
                }
            ]
        }
        public_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_one._id)
        res = app.put_json_api(
            url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

        res = app.get(public_project_one_url)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_public_projects_one_not_found
        payload = {'data': [
            {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                    'title': new_title,
                    'category': new_category
                }
            }, public_payload['data'][0]
        ]}

        res = app.put_json_api(
            url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

        public_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_one._id)
        res = app.get(public_project_one_url)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_public_projects_logged_out
        res = app.put_json_api(
            url, public_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        public_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_one._id)
        public_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_two._id)

        res = app.get(public_project_one_url)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(public_project_two_url)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_private_projects_logged_out
        res = app.put_json_api(
            url, private_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        private_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_one._id)
        private_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_two._id)

        res = app.get(private_project_one_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(private_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_private_projects_logged_in_non_contrib
        non_contrib = AuthUserFactory()
        res = app.put_json_api(
            url, private_payload,
            auth=non_contrib.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        private_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_one._id)
        private_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_two._id)

        res = app.get(private_project_one_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(private_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_projects_send_dictionary_not_list
        res = app.put_json_api(
            url,
            {'data': {
                'id': public_project_one._id,
                'type': 'nodes',
                'attributes': {
                    'title': new_title,
                    'category': 'project'
                }
            }},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_update_error_formatting
        res = app.put_json_api(
            url, empty_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = res.json['errors']
        assert errors[0]['source'] == {'pointer': '/data/0/attributes/title'}
        assert errors[1]['source'] == {'pointer': '/data/1/attributes/title'}
        assert errors[0]['detail'] == 'This field may not be blank.'
        assert errors[1]['detail'] == 'This field may not be blank.'

    #   test_bulk_update_id_not_supplied
        res = app.put_json_api(
            url,
            {'data': [
                public_payload['data'][1],
                {
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'category': new_category
                    }
                }
            ]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/id'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

        public_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_two._id)

        res = app.get(public_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_type_not_supplied
        res = app.put_json_api(
            url,
            {'data': [
                public_payload['data'][1],
                {
                    'id': public_project_one._id,
                    'attributes': {
                        'title': new_title,
                        'category': new_category
                    }
                }
            ]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/type'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

        public_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_two._id)

        res = app.get(public_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_incorrect_type
        res = app.put_json_api(
            url,
            {
                'data': [
                    public_payload['data'][1],
                    {
                        'id': public_project_one._id,
                        'type': 'Incorrect',
                        'attributes': {
                            'title': new_title,
                            'category': new_category
                        }
                    }
                ]
            },
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409

        public_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_two._id)

        res = app.get(public_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_update_limits
        node_update_list = {'data': [public_payload['data'][0]] * 101}
        res = app.put_json_api(
            url, node_update_list, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_bulk_update_no_title_or_category
        new_payload = {
            'id': public_project_one._id,
            'type': 'nodes',
            'attributes': {}}
        res = app.put_json_api(
            url,
            {'data': [
                public_payload['data'][1],
                new_payload
            ]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

        public_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_two._id)

        res = app.get(public_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    def test_bulk_update_private_projects_logged_in_read_only_contrib(
            self, app, user, private_project_one, private_project_two,
            title, private_payload, url):
        read_contrib = AuthUserFactory()
        private_project_one.add_contributor(
            read_contrib, permissions=[permissions.READ], save=True)
        private_project_two.add_contributor(
            read_contrib, permissions=[permissions.READ], save=True)
        res = app.put_json_api(
            url, private_payload,
            auth=read_contrib.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        private_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_one._id)
        private_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_two._id)

        res = app.get(private_project_one_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(private_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    def test_bulk_update_public_projects_logged_in(
            self, app, user, public_project_one,
            public_project_two, public_payload,
            new_title, url):
        res = app.put_json_api(url, public_payload, auth=user.auth, bulk=True)
        assert res.status_code == 200
        assert ({public_project_one._id, public_project_two._id} ==
                {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert res.json['data'][0]['attributes']['title'] == new_title
        assert res.json['data'][1]['attributes']['title'] == new_title

    def test_bulk_update_with_tags(self, app, user, public_project_one, url):
        new_payload = {
            'data': [{
                'id': public_project_one._id,
                'type': 'nodes',
                'attributes': {
                    'title': 'New title',
                    'category': 'project',
                    'tags': ['new tag']
                }
            }]
        }

        res = app.put_json_api(
            url, new_payload,
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['tags'] == ['new tag']

    def test_bulk_update_private_projects_logged_in_contrib(
            self, app, user, private_project_one,
            private_project_two, private_payload,
            new_title, url):
        res = app.put_json_api(url, private_payload, auth=user.auth, bulk=True)
        assert res.status_code == 200
        assert ({private_project_one._id, private_project_two._id} == {
                res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert res.json['data'][0]['attributes']['title'] == new_title
        assert res.json['data'][1]['attributes']['title'] == new_title


@pytest.mark.django_db
class TestNodeBulkPartialUpdate:

    @pytest.fixture()
    def title(self):
        return 'Rachel is great'

    @pytest.fixture()
    def new_title(self):
        return 'Rachel is awesome'

    @pytest.fixture()
    def description(self):
        return 'Such a cool person'

    @pytest.fixture()
    def new_description(self):
        return 'Such an amazing person'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def new_category(self):
        return 'project'

    @pytest.fixture()
    def public_project_one(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user)

    @pytest.fixture()
    def public_project_two(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user)

    @pytest.fixture()
    def public_payload(
            self, public_project_one, public_project_two, new_title):
        return {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                    }
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                    }
                }
            ]
        }

    @pytest.fixture()
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def private_project_one(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user)

    @pytest.fixture()
    def private_project_two(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user)

    @pytest.fixture()
    def private_payload(
            self, private_project_one, private_project_two, new_title):
        return {
            'data': [
                {
                    'id': private_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title
                    }
                },
                {
                    'id': private_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title
                    }
                }
            ]
        }

    @pytest.fixture()
    def empty_payload(self, public_project_one, public_project_two):
        return {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': ''
                    }
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': ''
                    }
                }
            ]
        }

    def test_bulk_partial_update_errors(
            self, app, user, public_project_one,
            public_project_two, private_project_one,
            private_project_two, title, new_title,
            public_payload, private_payload,
            empty_payload, url):

        #   test_bulk_patch_nodes_blank_request
        res = app.patch_json_api(
            url, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_partial_update_public_projects_one_not_found
        payload = {'data': [
            {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                    'title': new_title
                }
            },
            public_payload['data'][0]
        ]}
        res = app.patch_json_api(
            url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

        public_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_one._id)
        res = app.get(public_project_one_url)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_partial_update_public_projects_logged_out
        res = app.patch_json_api(
            url, public_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        public_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_one._id)
        public_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, public_project_two._id)

        res = app.get(public_project_one_url)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(public_project_two_url)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_partial_update_private_projects_logged_out
        res = app.patch_json_api(
            url, private_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        private_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_one._id)
        private_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_two._id)

        res = app.get(private_project_one_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(private_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_partial_update_private_projects_logged_in_non_contrib
        non_contrib = AuthUserFactory()
        res = app.patch_json_api(
            url, private_payload,
            auth=non_contrib.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        private_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_one._id)
        private_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_two._id)

        res = app.get(private_project_one_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(private_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    #   test_bulk_partial_update_projects_send_dictionary_not_list
        res = app.patch_json_api(
            url,
            {'data': {
                'id': public_project_one._id,
                'attributes': {
                    'title': new_title,
                    'category': 'project'
                }
            }},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_partial_update_error_formatting
        res = app.patch_json_api(
            url, empty_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = res.json['errors']
        assert errors[0]['source'] == {'pointer': '/data/0/attributes/title'}
        assert errors[1]['source'] == {'pointer': '/data/1/attributes/title'}
        assert errors[0]['detail'] == 'This field may not be blank.'
        assert errors[1]['detail'] == 'This field may not be blank.'

    #   test_bulk_partial_update_id_not_supplied
        res = app.patch_json_api(
            url,
            {
                'data': [{
                    'type': 'nodes',
                    'attributes': {'title': new_title}
                }]
            }, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

    #   test_bulk_partial_update_limits
        node_update_list = {'data': [public_payload['data'][0]] * 101}
        res = app.patch_json_api(
            url, node_update_list, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    def test_bulk_partial_update_public_projects_logged_in(
            self, app, user, public_project_one, public_project_two,
            new_title, public_payload, url):
        res = app.patch_json_api(
            url, public_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 200
        assert ({public_project_one._id, public_project_two._id} ==
                {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert res.json['data'][0]['attributes']['title'] == new_title
        assert res.json['data'][1]['attributes']['title'] == new_title

    def test_bulk_partial_update_private_projects_logged_in_contrib(
            self, app, user, private_project_one, private_project_two,
            new_title, private_payload, url):
        res = app.patch_json_api(
            url, private_payload, auth=user.auth, bulk=True)
        assert res.status_code == 200
        assert ({private_project_one._id, private_project_two._id} ==
                {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert res.json['data'][0]['attributes']['title'] == new_title
        assert res.json['data'][1]['attributes']['title'] == new_title

    def test_bulk_partial_update_private_projects_logged_in_read_only_contrib(
            self, app, user, private_project_one, private_project_two,
            title, private_payload, url):
        read_contrib = AuthUserFactory()
        private_project_one.add_contributor(
            read_contrib, permissions=[permissions.READ], save=True)
        private_project_two.add_contributor(
            read_contrib, permissions=[permissions.READ], save=True)
        res = app.patch_json_api(
            url, private_payload, auth=read_contrib.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        private_project_one_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_one._id)
        private_project_two_url = '/{}nodes/{}/'.format(
            API_BASE, private_project_two._id)

        res = app.get(private_project_one_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(private_project_two_url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == title

    def test_bulk_partial_update_privacy_has_no_effect_on_tags(
            self, app, user, public_project_one, url):
        public_project_one.add_tag('tag1', Auth(
            public_project_one.creator), save=True)
        payload = {
            'id': public_project_one._id,
            'type': 'nodes',
            'attributes': {
                'public': False}}
        res = app.patch_json_api(
            url, {'data': [payload]},
            auth=user.auth, bulk=True)
        assert res.status_code == 200
        public_project_one.reload()
        assert list(
            public_project_one.tags.values_list('name', flat=True)
        ) == ['tag1']
        assert public_project_one.is_public is False


@pytest.mark.django_db
class TestNodeBulkUpdateSkipUneditable:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def title(self):
        return 'A painting of reason'

    @pytest.fixture()
    def new_title(self):
        return 'A reason for painting'

    @pytest.fixture()
    def description(self):
        return 'Truly a masterful work of reasoning'

    @pytest.fixture()
    def new_description(self):
        return 'An insight into the reason for art'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def new_category(self):
        return 'project'

    @pytest.fixture()
    def user_one_public_project_one(
            self, user_one, title,
            description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def user_one_public_project_two(
            self, user_one, title,
            description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def user_two_public_project_one(
            self, user_two, title,
            description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def user_two_public_project_two(
            self, user_two, title,
            description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def public_payload(
            self, user_one_public_project_one,
            user_one_public_project_two,
            user_two_public_project_one,
            user_two_public_project_two,
            new_title, new_description,
            new_category):
        return {
            'data': [
                {
                    'id': user_one_public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': True
                    }
                },
                {
                    'id': user_one_public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': True
                    }
                },
                {
                    'id': user_two_public_project_one._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': True
                    }
                },
                {
                    'id': user_two_public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title,
                        'description': new_description,
                        'category': new_category,
                        'public': True
                    }
                }
            ]
        }

    @pytest.fixture()
    def url(self):
        return '/{}nodes/?skip_uneditable=True'.format(API_BASE)

    def test_bulk_update_skips(
            self, app, user_one,
            user_one_public_project_one,
            user_one_public_project_two,
            user_two_public_project_one,
            user_two_public_project_two,
            title, public_payload):

        #   test_skip_uneditable_bulk_update_query_param_required
        nodes_url = '/{}nodes/'.format(API_BASE)
        res = app.put_json_api(
            nodes_url, public_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        user_one_public_project_one.reload()
        user_one_public_project_two.reload()
        user_two_public_project_one.reload()
        user_two_public_project_two.reload()

        assert user_one_public_project_one.title == title
        assert user_one_public_project_two.title == title
        assert user_two_public_project_one.title == title
        assert user_two_public_project_two.title == title

    #   test_skip_uneditable_equals_false_bulk_update
        skip_uneditable_url = '/{}nodes/?skip_uneditable=False'.format(
            API_BASE)
        res = app.put_json_api(
            skip_uneditable_url,
            public_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        user_one_public_project_one.reload()
        user_one_public_project_two.reload()
        user_two_public_project_one.reload()
        user_two_public_project_two.reload()

        assert user_one_public_project_one.title == title
        assert user_one_public_project_two.title == title
        assert user_two_public_project_one.title == title
        assert user_two_public_project_two.title == title

    #   test_skip_uneditable_bulk_partial_update_query_param_required
        url = '/{}nodes/'.format(API_BASE)
        res = app.patch_json_api(
            url, public_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        user_one_public_project_one.reload()
        user_one_public_project_two.reload()
        user_two_public_project_one.reload()
        user_two_public_project_two.reload()

        assert user_one_public_project_one.title == title
        assert user_one_public_project_two.title == title
        assert user_two_public_project_one.title == title
        assert user_two_public_project_two.title == title

    def test_skip_uneditable_bulk_update(
            self, app, user_one,
            user_one_public_project_one,
            user_one_public_project_two,
            user_two_public_project_one,
            user_two_public_project_two,
            title, new_title, public_payload, url):
        res = app.put_json_api(
            url, public_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 200
        edited = res.json['data']
        skipped = res.json['errors']
        assert_items_equal(
            [edited[0]['id'], edited[1]['id']],
            [user_one_public_project_one._id,
             user_one_public_project_two._id]
        )
        assert_items_equal(
            [skipped[0]['_id'], skipped[1]['_id']],
            [user_two_public_project_one._id,
             user_two_public_project_two._id]
        )
        user_one_public_project_one.reload()
        user_one_public_project_two.reload()
        user_two_public_project_one.reload()
        user_two_public_project_two.reload()

        assert user_one_public_project_one.title == new_title
        assert user_one_public_project_two.title == new_title
        assert user_two_public_project_one.title == title
        assert user_two_public_project_two.title == title

    def test_skip_uneditable_bulk_partial_update(
            self, app, user_one,
            user_one_public_project_one,
            user_one_public_project_two,
            user_two_public_project_one,
            user_two_public_project_two,
            title, new_title, public_payload, url):
        res = app.patch_json_api(
            url, public_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 200
        edited = res.json['data']
        skipped = res.json['errors']
        assert_items_equal(
            [edited[0]['id'], edited[1]['id']],
            [user_one_public_project_one._id,
             user_one_public_project_two._id]
        )
        assert_items_equal(
            [skipped[0]['_id'], skipped[1]['_id']],
            [user_two_public_project_one._id,
             user_two_public_project_two._id]
        )
        user_one_public_project_one.reload()
        user_one_public_project_two.reload()
        user_two_public_project_one.reload()
        user_two_public_project_two.reload()

        assert user_one_public_project_one.title == new_title
        assert user_one_public_project_two.title == new_title
        assert user_two_public_project_one.title == title
        assert user_two_public_project_two.title == title


@pytest.mark.django_db
class TestNodeBulkDelete:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project_one(self, user_one):
        return ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user_one,
            category='project')

    @pytest.fixture()
    def public_project_two(self, user_one):
        return ProjectFactory(
            title='Project Two',
            description='One Three',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def public_project_parent(self, user_one):
        return ProjectFactory(
            title='Project with Component',
            description='Project with component',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def public_component(self, user_one, public_project_parent):
        return NodeFactory(parent=public_project_parent, creator=user_one)

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
    def url(self):
        return '/{}nodes/'.format(API_BASE)

    @pytest.fixture()
    def public_project_one_url(self, public_project_one):
        return '/{}nodes/{}/'.format(API_BASE, public_project_one._id)

    @pytest.fixture()
    def public_project_two_url(self, public_project_two):
        return '/{}nodes/{}/'.format(API_BASE, public_project_two._id)

    @pytest.fixture()
    def user_one_private_project_url(self, user_one_private_project):
        return '/{}nodes/{}/'.format(API_BASE, user_one_private_project._id)

    @pytest.fixture()
    def public_payload(self, public_project_one, public_project_two):
        return {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes'
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes'
                }
            ]
        }

    @pytest.fixture()
    def public_query_params(self, public_project_one, public_project_two):
        return 'id={},{}'.format(
            public_project_one._id,
            public_project_two._id)

    @pytest.fixture()
    def type_query_param(self):
        return 'type=nodes'

    @pytest.fixture()
    def private_payload(self, user_one_private_project):
        return {
            'data': [
                {
                    'id': user_one_private_project._id,
                    'type': 'nodes'
                }
            ]
        }

    @pytest.fixture()
    def private_query_params(self, user_one_private_project):
        return 'id={}'.format(user_one_private_project._id)

    def test_bulk_delete_errors(
            self, app, user_one, public_project_one,
            public_project_two, user_one_private_project,
            public_payload, private_payload,
            type_query_param, public_query_params, url):

        #   test_bulk_delete_with_query_params_and_payload
        res_url = '{}?{}&{}'.format(url, type_query_param, public_query_params)
        res = app.delete_json_api(
            res_url, public_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == u'A bulk DELETE can only have a body or query parameters, not both.'

    #   test_bulk_delete_with_query_params_no_type
        res_url = '{}?{}'.format(url, public_query_params)
        res = app.delete_json_api(
            res_url, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == u'Type query parameter is also required for a bulk DELETE using query parameters.'

    #   test_bulk_delete_with_query_params_wrong_type
        res_url = '{}?{}&{}'.format(
            url, public_query_params, 'type=node_not_nodes')
        res = app.delete_json_api(
            res_url, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == u'Type needs to match type expected at this endpoint.'

    #   test_bulk_delete_nodes_blank_request
        res = app.delete_json_api(
            url, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_delete_no_type
        payload = {'data': [
            {'id': public_project_one._id},
            {'id': public_project_two._id}
        ]}
        res = app.delete_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /type.'

    #   test_bulk_delete_no_id
        payload = {'data': [
            {'type': 'nodes'},
            {'id': 'nodes'}
        ]}
        res = app.delete_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/id.'

    #   test_bulk_delete_dict_inside_data
        res = app.delete_json_api(
            url,
            {'data': {
                'id': public_project_one._id,
                'type': 'nodes'
            }},
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_delete_invalid_type
        res = app.delete_json_api(
            url,
            {'data': [{
                'type': 'Wrong type',
                'id': public_project_one._id
            }]},
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409

    #   test_bulk_delete_private_projects_logged_out
        res = app.delete_json_api(
            url, private_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_bulk_delete_limits
        new_payload = {
            'data': [{
                'id': user_one_private_project._id,
                'type': 'nodes'
            }] * 101
        }
        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_bulk_delete_no_payload
        res = app.delete_json_api(
            url, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    def test_bulk_delete_with_query_params(
            self, app, user_one, url,
            type_query_param, public_query_params):
        url = '{}?{}&{}'.format(url, type_query_param, public_query_params)
        res = app.delete_json_api(url, auth=user_one.auth, bulk=True)
        assert res.status_code == 204

    def test_bulk_delete_public_projects_logged_in(
            self, app, user_one,
            public_project_one,
            public_project_two,
            public_payload,
            url, public_project_one_url):
        res = app.delete_json_api(
            url, public_payload,
            auth=user_one.auth, bulk=True)
        assert res.status_code == 204

        res = app.get(
            public_project_one_url,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 410
        public_project_one.reload()
        public_project_two.reload()

    def test_bulk_delete_public_projects_logged_out(
            self, app, user_one, public_payload,
            url, public_project_one_url,
            public_project_two_url):
        res = app.delete_json_api(
            url, public_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        res = app.get(
            public_project_one_url,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 200

        res = app.get(
            public_project_two_url,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 200

    def test_bulk_delete_private_projects_logged_in_contributor(
            self, app, user_one,
            user_one_private_project,
            private_payload, url,
            user_one_private_project_url):
        res = app.delete_json_api(
            url, private_payload,
            auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 204

        res = app.get(
            user_one_private_project_url,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 410
        user_one_private_project.reload()

    def test_bulk_delete_private_projects_logged_in_non_contributor(
            self, app, user_one, user_two,
            private_payload,
            url, user_one_private_project_url):
        res = app.delete_json_api(
            url, private_payload,
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        res = app.get(user_one_private_project_url, auth=user_one.auth)
        assert res.status_code == 200

    def test_bulk_delete_private_projects_logged_in_read_only_contributor(
            self, app, user_one, user_two,
            user_one_private_project,
            private_payload, url,
            user_one_private_project_url):
        user_one_private_project.add_contributor(
            user_two, permissions=[permissions.READ], save=True)
        res = app.delete_json_api(
            url, private_payload,
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        res = app.get(user_one_private_project_url, auth=user_one.auth)
        assert res.status_code == 200

    def test_bulk_delete_all_or_nothing(
            self, app, user_one, user_two,
            user_one_private_project,
            user_two_private_project, url,
            user_one_private_project_url):
        new_payload = {'data': [
            {'id': user_one_private_project._id, 'type': 'nodes'},
            {'id': user_two_private_project._id, 'type': 'nodes'}
        ]}
        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        res = app.get(user_one_private_project_url, auth=user_one.auth)
        assert res.status_code == 200

        url = '/{}nodes/{}/'.format(API_BASE, user_two_private_project._id)
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

    def test_bulk_delete_invalid_payload_one_not_found(
            self, app, user_one, public_payload, public_project_one_url, url):
        new_payload = {
            'data': [
                public_payload['data'][0], {
                    'id': '12345', 'type': 'nodes'}
            ]
        }
        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to delete.'

        res = app.get(public_project_one_url, auth=user_one.auth)
        assert res.status_code == 200

    def test_bulk_delete_project_with_component(
            self, app, user_one,
            public_project_parent,
            public_project_one,
            public_component, url):

        new_payload = {'data': [
            {'id': public_project_parent._id, 'type': 'nodes'},
            {'id': public_project_one._id, 'type': 'nodes'}
        ]}
        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

        new_payload = {'data': [
            {'id': public_project_parent._id, 'type': 'nodes'},
            {'id': public_component._id, 'type': 'nodes'}
        ]}
        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth, bulk=True)
        assert res.status_code == 204

    # Regression test for PLAT-859
    def test_bulk_delete_project_with_already_deleted_component(
            self, app, user_one,
            public_project_parent,
            public_project_one,
            public_component, url):

        public_component.is_deleted = True
        public_component.save()

        new_payload = {'data': [
            {'id': public_project_parent._id, 'type': 'nodes'},
            {'id': public_project_one._id, 'type': 'nodes'}
        ]}

        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth, bulk=True)
        assert res.status_code == 204

    # Regression test for PLAT-889
    def test_bulk_delete_project_with_linked_node(
            self, app, user_one,
            public_project_parent,
            public_component, url):

        node_link = NodeFactory(is_public=True, creator=user_one)
        public_project_parent.add_pointer(node_link, auth=Auth(user_one))

        new_payload = {'data': [
            {'id': public_project_parent._id, 'type': 'nodes'},
            {'id': public_component._id, 'type': 'nodes'}
        ]}

        res = app.delete_json_api(
            url, new_payload, auth=user_one.auth, bulk=True)
        assert res.status_code == 204


@pytest.mark.django_db
class TestNodeBulkDeleteSkipUneditable:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project_one(self, user_one):
        return ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def public_project_two(self, user_one):
        return ProjectFactory(
            title='Project Two',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def public_project_three(self, user_two):
        return ProjectFactory(
            title='Project Three',
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def public_project_four(self, user_two):
        return ProjectFactory(
            title='Project Four',
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def payload(
            self, public_project_one,
            public_project_two,
            public_project_three,
            public_project_four):
        return {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                },
                {
                    'id': public_project_three._id,
                    'type': 'nodes',
                },
                {
                    'id': public_project_four._id,
                    'type': 'nodes',
                }
            ]
        }

    @pytest.fixture()
    def url(self):
        return '/{}nodes/?skip_uneditable=True'.format(API_BASE)

    def test_skip_uneditable_bulk_delete(
            self, app, user_one,
            public_project_three,
            public_project_four,
            payload, url):
        res = app.delete_json_api(url, payload, auth=user_one.auth, bulk=True)
        assert res.status_code == 200
        skipped = res.json['errors']
        assert_items_equal(
            [skipped[0]['id'], skipped[1]['id']],
            [public_project_three._id, public_project_four._id]
        )

        res = app.get('/{}nodes/'.format(API_BASE), auth=user_one.auth)
        assert_items_equal(
            [res.json['data'][0]['id'], res.json['data'][1]['id']],
            [public_project_three._id, public_project_four._id]
        )

    def test_skip_uneditable_bulk_delete_query_param_required(
            self, app, user_one, payload):
        url = '/{}nodes/'.format(API_BASE)
        res = app.delete_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get('/{}nodes/'.format(API_BASE), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 4

    def test_skip_uneditable_has_admin_permission_for_all_nodes(
            self, app, user_one, public_project_one, public_project_two, url):
        payload = {
            'data': [
                {
                    'id': public_project_one._id,
                    'type': 'nodes',
                },
                {
                    'id': public_project_two._id,
                    'type': 'nodes',
                }
            ]
        }

        res = app.delete_json_api(url, payload, auth=user_one.auth, bulk=True)
        assert res.status_code == 204
        public_project_one.reload()
        public_project_two.reload()

        assert public_project_one.is_deleted is True
        assert public_project_two.is_deleted is True

    def test_skip_uneditable_does_not_have_admin_permission_for_any_nodes(
            self, app, user_one, public_project_three, public_project_four, url):
        payload = {
            'data': [
                {
                    'id': public_project_three._id,
                    'type': 'nodes',
                },
                {
                    'id': public_project_four._id,
                    'type': 'nodes',
                }
            ]
        }

        res = app.delete_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestNodeListPagination:

    @pytest.fixture()
    def users(self):
        return [UserFactory() for _ in range(11)]

    @pytest.fixture()
    def projects(self, users):
        return [
            ProjectFactory(
                is_public=True, creator=users[0]
            ) for _ in range(11)
        ]

    @pytest.fixture()
    def url(self, users):
        return '/{}nodes/'.format(API_BASE)

    def test_default_pagination_size(self, app, users, projects, url):
        res = app.get(url, auth=Auth(users[0]))
        pids = [e['id'] for e in res.json['data']]
        for project in projects[1:]:
            assert project._id in pids
        assert projects[0]._id not in pids
        assert res.json['links']['meta']['per_page'] == 10

    def test_max_page_size_enforced(self, app, users, projects, url):
        res_url = '{}?page[size]={}'.format(url, MAX_PAGE_SIZE + 1)
        res = app.get(res_url, auth=Auth(users[0]))
        pids = [e['id'] for e in res.json['data']]
        for project in projects:
            assert project._id in pids
        assert res.json['links']['meta']['per_page'] == MAX_PAGE_SIZE

    def test_embed_page_size_not_affected(self, app, users, projects, url):
        for user in users[1:]:
            projects[-1].add_contributor(user, auth=Auth(users[0]), save=True)

        res_url = '{}?page[size]={}&embed=contributors'.format(
            url, MAX_PAGE_SIZE + 1)
        res = app.get(res_url, auth=Auth(users[0]))
        pids = [e['id'] for e in res.json['data']]
        for project in projects:
            assert project._id in pids
        assert res.json['links']['meta']['per_page'] == MAX_PAGE_SIZE

        uids = [
            e['id'] for e in res.json['data'][0]['embeds']['contributors']['data']
        ]
        for user in users[:9]:
            contrib_id = '{}-{}'.format(res.json['data'][0]['id'], user._id)
            assert contrib_id in uids

        assert '{}-{}'.format(
            res.json['data'][0]['id'], users[10]._id
        ) not in uids
        assert res.json['data'][0]['embeds']['contributors']['links']['meta']['per_page'] == 10


@pytest.mark.django_db
class TestNodeListFiltering(NodesListFilteringMixin):

    @pytest.fixture()
    def url(self):
        return '/{}nodes/?'.format(API_BASE)


@pytest.mark.django_db
class TestNodeListDateFiltering(NodesListDateFilteringMixin):

    @pytest.fixture()
    def url(self):
        return '/{}nodes/?'.format(API_BASE)
