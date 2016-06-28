# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from modularodm import Q
from framework.auth.core import Auth

from website.models import Node, NodeLog
from website.util import permissions
from website.util.sanitize import strip_html

from api.base.settings.defaults import API_BASE, MAX_PAGE_SIZE

from tests.base import ApiTestCase
from tests.factories import (
    BookmarkCollectionFactory,
    CollectionFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    UserFactory,
)


class TestNodeList(ApiTestCase):
    def setUp(self):
        super(TestNodeList, self).setUp()
        self.user = AuthUserFactory()

        self.non_contrib = AuthUserFactory()

        self.deleted = ProjectFactory(is_deleted=True)
        self.private = ProjectFactory(is_public=False, creator=self.user)
        self.public = ProjectFactory(is_public=True, creator=self.user)

        self.url = '/{}nodes/'.format(API_BASE)

    def tearDown(self):
        super(TestNodeList, self).tearDown()
        Node.remove()

    def test_only_returns_non_deleted_public_projects(self):
        res = self.app.get(self.url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public._id, ids)
        assert_not_in(self.deleted._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_node_list_logged_out_user(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_node_list_logged_in_user(self):
        res = self.app.get(self.url, auth=self.non_contrib)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_out_user(self):
        res = self.app.get(self.url)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_node_list_does_not_returns_registrations(self):
        registration = RegistrationFactory(project=self.public, creator=self.user)
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_not_in(registration._id, ids)

    def test_node_list_has_root(self):
        res = self.app.get(self.url, auth=self.user.auth)
        projects_with_root = 0
        for project in res.json['data']:
            if project['relationships'].get('root', None):
                projects_with_root += 1
        assert_not_equal(projects_with_root, 0)
        assert_true(
            all([each['relationships'].get(
                'root'
            ) is not None for each in res.json['data']])
        )


    def test_node_list_has_proper_root(self):
        project_one = ProjectFactory(title="Project One", is_public=True)
        ProjectFactory(parent=project_one, is_public=True)

        res = self.app.get(self.url+'?embed=root&embed=parent', auth=self.user.auth)

        for project_json in res.json['data']:
            project = Node.load(project_json['id'])
            assert_equal(project_json['embeds']['root']['data']['id'], project.root._id)



class TestNodeFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", is_public=True)
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True)
        self.project_three = ProjectFactory(title="Three", is_public=True)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)
        self.folder = CollectionFactory()
        self.bookmark_collection = BookmarkCollectionFactory()

        self.url = "/{}nodes/".format(API_BASE)

        self.tag1, self.tag2 = 'tag1', 'tag2'
        self.project_one.add_tag(self.tag1, Auth(self.project_one.creator), save=False)
        self.project_one.add_tag(self.tag2, Auth(self.project_one.creator), save=False)
        self.project_one.save()

        self.project_two.add_tag(self.tag1, Auth(self.project_two.creator), save=True)

    def tearDown(self):
        super(TestNodeFiltering, self).tearDown()
        Node.remove()

    def test_filtering_by_id(self):
        url = '/{}nodes/?filter[id]={}'.format(API_BASE, self.project_one._id)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.project_one._id, ids)
        assert_equal(len(ids), 1)

    def test_filtering_by_multiple_ids(self):
        url = '/{}nodes/?filter[id]={},{}'.format(API_BASE, self.project_one._id, self.project_two._id)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_equal(len(ids), 2)

    def test_filtering_by_multiple_ids_one_private(self):
        url = '/{}nodes/?filter[id]={},{}'.format(API_BASE, self.project_one._id, self.private_project_user_two._id)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.project_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_equal(len(ids), 1)

    def test_filtering_by_multiple_ids_brackets_in_query_params(self):
        url = '/{}nodes/?filter[id]=[{},   {}]'.format(API_BASE, self.project_one._id, self.project_two._id)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_equal(len(ids), 2)

    def test_filtering_by_category(self):
        project = ProjectFactory(creator=self.user_one, category='hypothesis')
        project2 = ProjectFactory(creator=self.user_one, category='procedure')
        url = '/{}nodes/?filter[category]=hypothesis'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)

        node_json = res.json['data']
        ids = [each['id'] for each in node_json]

        assert_in(project._id, ids)
        assert_not_in(project2._id, ids)

    def test_filtering_by_public(self):
        project = ProjectFactory(creator=self.user_one, is_public=True)
        project2 = ProjectFactory(creator=self.user_one, is_public=False)

        url = '/{}nodes/?filter[public]=false'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        # No public projects returned
        assert_false(
            any([each['attributes']['public'] for each in node_json])
        )

        ids = [each['id'] for each in node_json]
        assert_not_in(project._id, ids)
        assert_in(project2._id, ids)

        url = '/{}nodes/?filter[public]=true'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        # No private projects returned
        assert_true(
            all([each['attributes']['public'] for each in node_json])
        )

        ids = [each['id'] for each in node_json]
        assert_not_in(project2._id, ids)
        assert_in(project._id, ids)

    def test_filtering_tags(self):
        # both project_one and project_two have tag1
        url = '/{}nodes/?filter[tags]={}'.format(API_BASE, self.tag1)

        res = self.app.get(url, auth=self.project_one.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)

        # filtering two tags
        # project_one has both tags; project_two only has one
        url = '/{}nodes/?filter[tags]={}&filter[tags]={}'.format(API_BASE, self.tag1, self.tag2)

        res = self.app.get(url, auth=self.project_one.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)

    def test_get_all_projects_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_all_projects_with_no_filter_not_logged_in(self):
        res = self.app.get(self.url)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_one_project_with_exact_filter_logged_in(self):
        url = "/{}nodes/?filter[title]=Project%20One".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_one_project_with_exact_filter_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Project%20One".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_some_projects_with_substring_logged_in(self):
        url = "/{}nodes/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_some_projects_with_substring_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_only_public_or_my_projects_with_filter_logged_in(self):
        url = "/{}nodes/?filter[title]=Project".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_get_only_public_projects_with_filter_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Project".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_alternate_filtering_field_logged_in(self):
        url = "/{}nodes/?filter[description]=Three".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_alternate_filtering_field_not_logged_in(self):
        url = "/{}nodes/?filter[description]=Three".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.bookmark_collection._id, ids)

    def test_incorrect_filtering_field_not_logged_in(self):
        url = '/{}nodes/?filter[notafield]=bogus'.format(API_BASE)

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], "'notafield' is not a valid field for this endpoint.")

    def test_filtering_on_root(self):
        root = ProjectFactory(is_public=True)
        child = ProjectFactory(parent=root, is_public=True)
        ProjectFactory(parent=root, is_public=True)
        ProjectFactory(parent=child, is_public=True)
        # create some unrelated projects
        ProjectFactory(title="Road Dogg Jesse James", is_public=True)
        ProjectFactory(title="Badd *** Billy Gunn", is_public=True)

        url = '/{}nodes/?filter[root]={}'.format(API_BASE, root._id)

        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

        root_nodes = Node.find(Q('is_public', 'eq', True) & Q('root', 'eq', root._id))
        assert_equal(len(res.json['data']), root_nodes.count())

    def test_filtering_on_null_parent(self):
        # add some nodes TO be included
        new_user = AuthUserFactory()
        root = ProjectFactory(is_public=True)
        ProjectFactory(is_public=True)
        # Build up a some of nodes not to be included
        child = ProjectFactory(parent=root, is_public=True)
        ProjectFactory(parent=root, is_public=True)
        ProjectFactory(parent=child, is_public=True)

        url = '/{}nodes/?filter[parent]=null'.format(API_BASE)

        res = self.app.get(url, auth=new_user.auth)
        assert_equal(res.status_code, 200)

        public_root_nodes = Node.find(Q('is_public', 'eq', True) & Q('parent_node', 'eq', None))
        assert_equal(len(res.json['data']), public_root_nodes.count())

    def test_filtering_on_title_not_equal(self):
        url = '/{}nodes/?filter[title][ne]=Project%20One'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 3)

        titles = [each['attributes']['title'] for each in data]

        assert_not_in(self.project_one.title, titles)
        assert_in(self.project_two.title, titles)
        assert_in(self.project_three.title, titles)
        assert_in(self.private_project_user_one.title, titles)

    def test_filtering_on_description_not_equal(self):
        url = '/{}nodes/?filter[description][ne]=One%20Three'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 3)

        descriptions = [each['attributes']['description'] for each in data]

        assert_not_in(self.project_two.description, descriptions)
        assert_in(self.project_one.description, descriptions)
        assert_in(self.project_three.description, descriptions)
        assert_in(self.private_project_user_one.description, descriptions)


class TestNodeCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': self.title,
                        'description': self.description,
                        'category': self.category,
                        'public': True,
                    }
            }
        }
        self.private_project = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                }
            }
        }
    def test_node_create_invalid_data(self):
        res = self.app.post_json_api(self.url, "Incorrect data", auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.post_json_api(self.url, ["Incorrect data"], auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_creates_public_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.public_project, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_public_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.public_project, expect_errors=True, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.public_project['data']['attributes']['title'])
        assert_equal(res.json['data']['attributes']['description'], self.public_project['data']['attributes']['description'])
        assert_equal(res.json['data']['attributes']['category'], self.public_project['data']['attributes']['category'])
        assert_equal(res.content_type, 'application/vnd.api+json')
        pid = res.json['data']['id']
        project = Node.load(pid)
        assert_equal(project.logs[-1].action, NodeLog.PROJECT_CREATED)

    def test_creates_private_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.private_project, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_private_project_logged_in_contributor(self):
        res = self.app.post_json_api(self.url, self.private_project, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project['data']['attributes']['title'])
        assert_equal(res.json['data']['attributes']['description'], self.private_project['data']['attributes']['description'])
        assert_equal(res.json['data']['attributes']['category'], self.private_project['data']['attributes']['category'])
        pid = res.json['data']['id']
        project = Node.load(pid)
        assert_equal(project.logs[-1].action, NodeLog.PROJECT_CREATED)

    def test_creates_project_from_template(self):
        template_from = ProjectFactory(creator=self.user_one, is_public=True)
        template_component = ProjectFactory(creator=self.user_one, is_public=True, parent=template_from)
        templated_project_title = 'Templated Project'
        templated_project_data = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': templated_project_title,
                        'category': self.category,
                        'template_from': template_from._id,
                    }
            }
        }

        res = self.app.post_json_api(self.url, templated_project_data, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        json_data = res.json['data']

        new_project_id = json_data['id']
        new_project = Node.load(new_project_id)
        assert_equal(new_project.title, templated_project_title)
        assert_equal(new_project.description, None)
        assert_false(new_project.is_public)
        assert_equal(len(new_project.nodes), len(template_from.nodes))
        assert_equal(new_project.nodes[0].title, template_component.title)

    def test_404_on_create_from_template_of_nonexistent_project(self):
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
        res = self.app.post_json_api(self.url, templated_project_data, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_403_on_create_from_template_of_unauthorized_project(self):
        template_from = ProjectFactory(creator=self.user_two, is_public=True)
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
        res = self.app.post_json_api(self.url, templated_project_data, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_creates_project_creates_project_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> project'

        res = self.app.post_json_api(self.url, {
            'data': {
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': self.category,
                    'public': True
                },
                'type': 'nodes'
            }
        }, auth=self.user_one.auth)
        project_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = '/{}nodes/{}/'.format(API_BASE, project_id)

        project = Node.load(project_id)
        assert_equal(project.logs[-1].action, NodeLog.PROJECT_CREATED)

        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_create_component_inherit_contributors(self):
        parent_project = ProjectFactory(creator=self.user_one)
        parent_project.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        url = '/{}nodes/{}/children/{}'.format(API_BASE, parent_project._id, '?inherit_contributors=true')
        component_data = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'category': self.category,
                }
            }
        }
        res = self.app.post_json_api(url, component_data, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        json_data = res.json['data']

        new_component_id = json_data['id']
        new_component = Node.load(new_component_id)
        assert_equal(len(new_component.contributors), 2)
        assert_equal(len(new_component.contributors), len(parent_project.contributors))

    def test_creates_project_no_type(self):
        project = {
            'data': {
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                }
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_creates_project_incorrect_type(self):
        project = {
            'data': {
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                },
                'type': 'Wrong type.'
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'This resource has a type of "nodes", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.')

    def test_creates_project_properties_not_nested(self):
        project = {
            'data': {
                'title': self.title,
                'description': self.description,
                'category': self.category,
                'public': False,
                'type': 'nodes'
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/attributes.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

    def test_create_project_invalid_title(self):
        project = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': 'A' * 201,
                    'description': self.description,
                    'category': self.category,
                    'public': False,
                }
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Title cannot exceed 200 characters.')


class TestNodeBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': True
                }
        }

        self.private_project = {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                }
        }

        self.empty_project = {'type': 'nodes', 'attributes': {'title': "", 'description': "", "category": ""}}

    def test_bulk_create_nodes_blank_request(self):
        res = self.app.post_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_create_all_or_nothing(self):
        res = self.app.post_json_api(self.url, {'data': [self.public_project, self.empty_project]}, bulk=True, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_out(self):
        res = self.app.post_json_api(self.url, {'data': [self.public_project, self.private_project]}, bulk=True, expect_errors=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_error_formatting(self):
        res = self.app.post_json_api(self.url, {'data': [self.empty_project, self.empty_project]}, bulk=True, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ["This field may not be blank.", "This field may not be blank."])

    def test_bulk_create_limits(self):
        node_create_list = {'data': [self.public_project] * 101}
        res = self.app.post_json_api(self.url, node_create_list, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_type(self):
        payload = {'data': [{"attributes": {'category': self.category, 'title': self.title}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_incorrect_type(self):
        payload = {'data': [self.public_project, {'type': 'Incorrect type.', "attributes": {'category': self.category, 'title': self.title}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_attributes(self):
        payload = {'data': [self.public_project, {'type': 'nodes', }]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_title(self):
        payload = {'data': [self.public_project, {'type': 'nodes', "attributes": {'category': self.category}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/attributes/title')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_ugly_payload(self):
        payload = 'sdf;jlasfd'
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_in(self):
        res = self.app.post_json_api(self.url, {'data': [self.public_project, self.private_project]}, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['attributes']['title'], self.public_project['attributes']['title'])
        assert_equal(res.json['data'][0]['attributes']['category'], self.public_project['attributes']['category'])
        assert_equal(res.json['data'][0]['attributes']['description'], self.public_project['attributes']['description'])
        assert_equal(res.json['data'][1]['attributes']['title'], self.private_project['attributes']['title'])
        assert_equal(res.json['data'][1]['attributes']['category'], self.public_project['attributes']['category'])
        assert_equal(res.json['data'][1]['attributes']['description'], self.public_project['attributes']['description'])
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 2)
        id_one = res.json['data'][0]['id']
        id_two = res.json['data'][1]['id']

        res = self.app.delete_json_api(self.url, {'data': [{'id': id_one, 'type': 'nodes'},
                                                           {'id': id_two, 'type': 'nodes'}]},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 204)


class TestNodeBulkUpdate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'

        self.new_category = 'project'

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_project_two = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user)

        self.public_payload = {
            'data': [
                {
                    'id': self.public_project._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                },
                {
                    'id': self.public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                }
            ]
        }

        self.url = '/{}nodes/'.format(API_BASE)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_project_two = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_payload = {'data': [
                {
                    'id': self.private_project._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': False
                    }
                },
                {
                    'id': self.private_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': False
                    }
                }
            ]
        }


        self.empty_payload = {'data': [
            {'id': self.public_project._id, 'type': 'nodes', 'attributes': {'title': "", 'description': "", "category": ""}},
            {'id': self.public_project_two._id, 'type': 'nodes', 'attributes': {'title': "", 'description': "", "category": ""}}
        ]}

    def test_bulk_update_nodes_blank_request(self):
        res = self.app.put_json_api(self.url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_update_blank_but_not_empty_title(self):
        payload = {
            "data": [
                {
                  "id": self.public_project._id,
                  "type": "nodes",
                  "attributes": {
                    "title": "This shouldn't update.",
                    "category": "instrumentation"
                  }
                },
                {
                  "id": self.public_project_two._id,
                  "type": "nodes",
                  "attributes": {
                    "title": " ",
                    "category": "hypothesis"
                  }
                }
              ]
            }
        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_with_tags(self):
        new_payload = {'data': [{'id': self.public_project._id, 'type': 'nodes', 'attributes': {'title': 'New title', 'category': 'project', 'tags': ['new tag']}}]}

        res = self.app.put_json_api(self.url, new_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['tags'], ['new tag'])

    def test_bulk_update_public_projects_one_not_found(self):
        empty_payload = {'data': [
            {
                'id': 12345,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'category': self.new_category
                }
            }, self.public_payload['data'][0]
        ]}

        res = self.app.put_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')


        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)


    def test_bulk_update_public_projects_logged_out(self):
        res = self.app.put_json_api(self.url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_public_projects_logged_in(self):
        res = self.app.put_json_api(self.url, self.public_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.public_project._id, self.public_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_update_private_projects_logged_out(self):
        res = self.app.put_json_api(self.url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_private_projects_logged_in_contrib(self):
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.private_project._id, self.private_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_update_private_projects_logged_in_non_contrib(self):
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_private_projects_logged_in_read_only_contrib(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        self.private_project_two.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_projects_send_dictionary_not_list(self):
        res = self.app.put_json_api(self.url, {'data': {'id': self.public_project._id, 'type': 'nodes',
                                                        'attributes': {'title': self.new_title, 'category': "project"}}},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_update_error_formatting(self):
        res = self.app.put_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.'] * 2)

    def test_bulk_update_id_not_supplied(self):
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], {'type': 'nodes', 'attributes':
            {'title': self.new_title, 'category': self.new_category}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/id')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_type_not_supplied(self):
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], {'id': self.public_project._id, 'attributes':
            {'title': self.new_title, 'category': self.new_category}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/type')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_incorrect_type(self):
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], {'id': self.public_project._id, 'type': 'Incorrect', 'attributes':
            {'title': self.new_title, 'category': self.new_category}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_limits(self):
        node_update_list = {'data': [self.public_payload['data'][0]] * 101}
        res = self.app.put_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_update_no_title_or_category(self):
        new_payload = {'id': self.public_project._id, 'type': 'nodes', 'attributes': {}}
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], new_payload]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)


class TestNodeBulkPartialUpdate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkPartialUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'

        self.new_category = 'project'

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_project_two = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user)

        self.public_payload = {'data': [
            {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            },
            {
                'id': self.public_project_two._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        ]}

        self.url = '/{}nodes/'.format(API_BASE)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_project_two = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_payload = {'data': [
            {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            },
            {
                'id': self.private_project_two._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        ]}

        self.empty_payload = {'data': [
            {'id': self.public_project._id, 'type': 'nodes', 'attributes': {'title': ""}},
            {'id': self.public_project_two._id, 'type': 'nodes', 'attributes': {'title': ""}}
        ]
        }

    def test_bulk_patch_nodes_blank_request(self):
        res = self.app.patch_json_api(self.url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_partial_update_public_projects_one_not_found(self):
        empty_payload = {'data': [
            {
                'id': 12345,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            },
            self.public_payload['data'][0]
        ]}
        res = self.app.patch_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_public_projects_logged_out(self):
        res = self.app.patch_json_api(self.url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_public_projects_logged_in(self):
        res = self.app.patch_json_api(self.url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.public_project._id, self.public_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_partial_update_private_projects_logged_out(self):
        res = self.app.patch_json_api(self.url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_private_projects_logged_in_contrib(self):
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.private_project._id, self.private_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_partial_update_private_projects_logged_in_non_contrib(self):
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_private_projects_logged_in_read_only_contrib(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        self.private_project_two.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_projects_send_dictionary_not_list(self):
        res = self.app.patch_json_api(self.url, {'data': {'id': self.public_project._id, 'attributes': {'title': self.new_title, 'category': "project"}}},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_partial_update_error_formatting(self):
        res = self.app.patch_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.']*2)

    def test_bulk_partial_update_id_not_supplied(self):
        res = self.app.patch_json_api(self.url, {'data': [{'type': 'nodes', 'attributes': {'title': self.new_title}}]},
                                      auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')

    def test_bulk_partial_update_limits(self):
        node_update_list = {'data': [self.public_payload['data'][0]] * 101 }
        res = self.app.patch_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_partial_update_privacy_has_no_effect_on_tags(self):
        self.public_project.add_tag('tag1', Auth(self.public_project.creator), save=True)
        payload = {'id': self.public_project._id, 'type': 'nodes', 'attributes': {'public': False}}
        res = self.app.patch_json_api(self.url, {'data': [payload]}, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        self.public_project.reload()
        assert_equal(self.public_project.tags, ['tag1'])
        assert_equal(self.public_project.is_public, False)


class TestNodeBulkUpdateSkipUneditable(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkUpdateSkipUneditable, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'
        self.new_category = 'project'

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_project_two = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user)

        self.public_project_three = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user_two)

        self.public_project_four = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user_two)

        self.public_payload = {
            'data': [
                {
                    'id': self.public_project._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                },
                {
                    'id': self.public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                },
                 {
                    'id': self.public_project_three._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                },
                 {
                    'id': self.public_project_four._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                }
            ]
        }

        self.url = '/{}nodes/?skip_uneditable=True'.format(API_BASE)

    def test_skip_uneditable_bulk_update(self):
        res = self.app.put_json_api(self.url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 200)
        edited = res.json['data']
        skipped = res.json['errors']
        assert_items_equal([edited[0]['id'], edited[1]['id']],
                           [self.public_project._id, self.public_project_two._id])
        assert_items_equal([skipped[0]['_id'], skipped[1]['_id']],
                           [self.public_project_three._id, self.public_project_four._id])
        self.public_project.reload()
        self.public_project_two.reload()
        self.public_project_three.reload()
        self.public_project_four.reload()

        assert_equal(self.public_project.title, self.new_title)
        assert_equal(self.public_project_two.title, self.new_title)
        assert_equal(self.public_project_three.title, self.title)
        assert_equal(self.public_project_four.title, self.title)


    def test_skip_uneditable_bulk_update_query_param_required(self):
        url = '/{}nodes/'.format(API_BASE)
        res = self.app.put_json_api(url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        self.public_project.reload()
        self.public_project_two.reload()
        self.public_project_three.reload()
        self.public_project_four.reload()

        assert_equal(self.public_project.title, self.title)
        assert_equal(self.public_project_two.title, self.title)
        assert_equal(self.public_project_three.title, self.title)
        assert_equal(self.public_project_four.title, self.title)

    def test_skip_uneditable_equals_false_bulk_update(self):
        url = '/{}nodes/?skip_uneditable=False'.format(API_BASE)
        res = self.app.put_json_api(url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        self.public_project.reload()
        self.public_project_two.reload()
        self.public_project_three.reload()
        self.public_project_four.reload()

        assert_equal(self.public_project.title, self.title)
        assert_equal(self.public_project_two.title, self.title)
        assert_equal(self.public_project_three.title, self.title)
        assert_equal(self.public_project_four.title, self.title)

    def test_skip_uneditable_bulk_partial_update(self):
        res = self.app.patch_json_api(self.url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 200)
        edited = res.json['data']
        skipped = res.json['errors']
        assert_items_equal([edited[0]['id'], edited[1]['id']],
                           [self.public_project._id, self.public_project_two._id])
        assert_items_equal([skipped[0]['_id'], skipped[1]['_id']],
                           [self.public_project_three._id, self.public_project_four._id])
        self.public_project.reload()
        self.public_project_two.reload()
        self.public_project_three.reload()
        self.public_project_four.reload()

        assert_equal(self.public_project.title, self.new_title)
        assert_equal(self.public_project_two.title, self.new_title)
        assert_equal(self.public_project_three.title, self.title)
        assert_equal(self.public_project_four.title, self.title)


    def test_skip_uneditable_bulk_partial_update_query_param_required(self):
        url = '/{}nodes/'.format(API_BASE)
        res = self.app.patch_json_api(url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        self.public_project.reload()
        self.public_project_two.reload()
        self.public_project_three.reload()
        self.public_project_four.reload()

        assert_equal(self.public_project.title, self.title)
        assert_equal(self.public_project_two.title, self.title)
        assert_equal(self.public_project_three.title, self.title)
        assert_equal(self.public_project_four.title, self.title)


class TestNodeBulkDelete(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkDelete, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", is_public=True, creator=self.user_one, category="project")
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)

        self.url = "/{}nodes/".format(API_BASE)
        self.project_one_url = '/{}nodes/{}/'.format(API_BASE, self.project_one._id)
        self.project_two_url = '/{}nodes/{}/'.format(API_BASE, self.project_two._id)
        self.private_project_url = "/{}nodes/{}/".format(API_BASE, self.private_project_user_one._id)

        self.public_payload = {'data': [{'id': self.project_one._id, 'type': 'nodes'}, {'id': self.project_two._id, 'type': 'nodes'}]}
        self.private_payload = {'data': [{'id': self.private_project_user_one._id, 'type': 'nodes'}]}

    def test_bulk_delete_nodes_blank_request(self):
        res = self.app.delete_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_delete_no_type(self):
        payload = {'data': [
            {'id': self.project_one._id},
            {'id': self.project_two._id}
        ]}
        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')

    def test_bulk_delete_no_id(self):
        payload = {'data': [
            {'type': 'nodes'},
            {'id': 'nodes'}
        ]}
        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/id.')

    def test_bulk_delete_dict_inside_data(self):
        res = self.app.delete_json_api(self.url, {'data': {'id': self.project_one._id, 'type': 'nodes'}},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_delete_invalid_type(self):
        res = self.app.delete_json_api(self.url, {'data': [{'type': 'Wrong type', 'id': self.project_one._id}]},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_delete_public_projects_logged_in(self):
        res = self.app.delete_json_api(self.url, self.public_payload, auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.project_one.reload()
        self.project_two.reload()

    def test_bulk_delete_public_projects_logged_out(self):
        res = self.app.delete_json_api(self.url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        res = self.app.get(self.project_two_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_private_projects_logged_out(self):
        res = self.app.delete_json_api(self.url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_bulk_delete_private_projects_logged_in_contributor(self):
        res = self.app.delete_json_api(self.url, self.private_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.private_project_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.private_project_user_one.reload()

    def test_bulk_delete_private_projects_logged_in_non_contributor(self):
        res = self.app.delete_json_api(self.url, self.private_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_private_projects_logged_in_read_only_contributor(self):
        self.private_project_user_one.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.delete_json_api(self.url, self.private_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_all_or_nothing(self):
        new_payload = {'data': [{'id': self.private_project_user_one._id, 'type': 'nodes'}, {'id': self.private_project_user_two._id, 'type': 'nodes'}]}
        res = self.app.delete_json_api(self.url, new_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

        url = "/{}nodes/{}/".format(API_BASE, self.private_project_user_two._id)
        res = self.app.get(url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_limits(self):
        new_payload = {'data': [{'id': self.private_project_user_one._id, 'type':'nodes'}] * 101 }
        res = self.app.delete_json_api(self.url, new_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_delete_invalid_payload_one_not_found(self):
        new_payload = {'data': [self.public_payload['data'][0], {'id': '12345', 'type': 'nodes'}]}
        res = self.app.delete_json_api(self.url, new_payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to delete.')

        res = self.app.get(self.project_one_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_no_payload(self):
        res = self.app.delete_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)


class TestNodeBulkDeleteSkipUneditable(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkDeleteSkipUneditable, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", is_public=True, creator=self.user_one)
        self.project_two = ProjectFactory(title="Project Two",  is_public=True, creator=self.user_one)
        self.project_three = ProjectFactory(title="Project Three", is_public=True, creator=self.user_two)
        self.project_four = ProjectFactory(title="Project Four", is_public=True, creator=self.user_two)

        self.payload = {
            'data': [
                {
                    'id': self.project_one._id,
                    'type': 'nodes',
                },
                {
                    'id': self.project_two._id,
                    'type': 'nodes',
                },
                 {
                    'id': self.project_three._id,
                    'type': 'nodes',
                },
                 {
                    'id': self.project_four._id,
                    'type': 'nodes',
                }
            ]
        }



        self.url = "/{}nodes/?skip_uneditable=True".format(API_BASE)

    def tearDown(self):
        super(TestNodeBulkDeleteSkipUneditable, self).tearDown()
        Node.remove()

    def test_skip_uneditable_bulk_delete(self):
        res = self.app.delete_json_api(self.url, self.payload, auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 200)
        skipped = res.json['errors']
        assert_items_equal([skipped[0]['id'], skipped[1]['id']],
                           [self.project_three._id, self.project_four._id])

        res = self.app.get('/{}nodes/'.format(API_BASE), auth=self.user_one.auth)
        assert_items_equal([res.json['data'][0]['id'], res.json['data'][1]['id']],
                           [self.project_three._id, self.project_four._id])

    def test_skip_uneditable_bulk_delete_query_param_required(self):
        url = '/{}nodes/'.format(API_BASE)
        res = self.app.delete_json_api(url, self.payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get('/{}nodes/'.format(API_BASE), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 4)

    def test_skip_uneditable_has_admin_permission_for_all_nodes(self):
        payload = {
            'data': [
                {
                    'id': self.project_one._id,
                    'type': 'nodes',
                },
                {
                    'id': self.project_two._id,
                    'type': 'nodes',
                }
            ]
        }

        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 204)
        self.project_one.reload()
        self.project_two.reload()

        assert_equal(self.project_one.is_deleted, True)
        assert_equal(self.project_two.is_deleted, True)

    def test_skip_uneditable_does_not_have_admin_permission_for_any_nodes(self):
        payload = {
            'data': [
                {
                    'id': self.project_three._id,
                    'type': 'nodes',
                },
                {
                    'id': self.project_four._id,
                    'type': 'nodes',
                }
            ]
        }

        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)


class TestNodeListPagination(ApiTestCase):

    def setUp(self):
        super(TestNodeListPagination, self).setUp()

        # Ordered by date modified: oldest first
        self.users = [UserFactory() for _ in range(11)]
        self.projects = [ProjectFactory(is_public=True, creator=self.users[0]) for _ in range(11)]

        self.url = '/{}nodes/'.format(API_BASE)

    def tearDown(self):
        super(TestNodeListPagination, self).tearDown()
        Node.remove()

    def test_default_pagination_size(self):
        res = self.app.get(self.url, auth=Auth(self.users[0]))
        pids = [e['id'] for e in res.json['data']]
        for project in self.projects[1:]:
            assert_in(project._id, pids)
        assert_not_in(self.projects[0]._id, pids)
        assert_equal(res.json['links']['meta']['per_page'], 10)

    def test_max_page_size_enforced(self):
        url = '{}?page[size]={}'.format(self.url, MAX_PAGE_SIZE+1)
        res = self.app.get(url, auth=Auth(self.users[0]))
        pids = [e['id'] for e in res.json['data']]
        for project in self.projects:
            assert_in(project._id, pids)
        assert_equal(res.json['links']['meta']['per_page'], MAX_PAGE_SIZE)

    def test_embed_page_size_not_affected(self):
        for user in self.users[1:]:
            self.projects[-1].add_contributor(user, auth=Auth(self.users[0]), save=True)

        url = '{}?page[size]={}&embed=contributors'.format(self.url, MAX_PAGE_SIZE+1)
        res = self.app.get(url, auth=Auth(self.users[0]))
        pids = [e['id'] for e in res.json['data']]
        for project in self.projects:
            assert_in(project._id, pids)
        assert_equal(res.json['links']['meta']['per_page'], MAX_PAGE_SIZE)

        uids = [e['id'] for e in res.json['data'][0]['embeds']['contributors']['data']]
        for user in self.users[:9]:
            assert_in(user._id, uids)
        assert_not_in(self.users[10]._id, uids)
        assert_equal(res.json['data'][0]['embeds']['contributors']['links']['meta']['per_page'], 10)
