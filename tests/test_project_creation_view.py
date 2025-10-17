"""Views tests for the OSF."""
import pytest
from framework.auth import Auth
from osf.models import (
    AbstractNode,
)
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    ProjectWithAddonFactory,
)
from tests.base import (
    OsfTestCase,
)
from website.util import api_url_for, web_url_for

@pytest.mark.enable_implicit_clean
@pytest.mark.enable_bookmark_creation
class TestProjectCreation(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.url = api_url_for('project_new_post')
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user1)
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

    def tearDown(self):
        super().tearDown()

    def test_needs_title(self):
        res = self.app.post(self.url, json={}, auth=self.creator.auth)
        assert res.status_code == 400

    def test_create_component_strips_html(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        url = web_url_for('project_new_node', pid=project._id)
        post_data = {'title': '<b>New <blink>Component</blink> Title</b>', 'category': ''}
        self.app.post(url, data=post_data, auth=user.auth, follow_redirects=True)
        project.reload()
        child = project.nodes[0]
        # HTML has been stripped
        assert child.title == 'New Component Title'

    def test_strip_html_from_title(self):
        payload = {
            'title': 'no html <b>here</b>'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert 'no html here' == node.title

    def test_only_needs_title(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201

    def test_title_must_be_one_long(self):
        payload = {
            'title': ''
        }
        res = self.app.post(
            self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 400

    def test_title_must_be_less_than_200(self):
        payload = {
            'title': ''.join([str(x) for x in range(0, 250)])
        }
        res = self.app.post(
            self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 400

    def test_fails_to_create_project_with_whitespace_title(self):
        payload = {
            'title': '   '
        }
        res = self.app.post(
            self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 400

    def test_creates_a_project(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert node.title == 'Im a real title'

    def test_create_component_add_contributors_admin(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, data=post_data, auth=self.user1.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert self.user1 in child.contributors
        assert self.user2 in child.contributors
        # check redirect url
        assert '/contributors/' in res.location

    def test_create_component_with_contributors_read_write(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        read_user = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=permissions.WRITE)
        self.project.add_contributor(read_user, permissions=permissions.READ)
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, data=post_data, auth=non_admin.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert non_admin in child.contributors
        assert self.user1 in child.contributors
        assert self.user2 in child.contributors
        assert read_user in child.contributors
        assert child.has_permission(non_admin, permissions.ADMIN) is True
        assert child.has_permission(non_admin, permissions.WRITE) is True
        assert child.has_permission(non_admin, permissions.READ) is True
        # read_user was a read contrib on the parent, but was an admin group member
        # read contrib perms copied over
        assert child.has_permission(read_user, permissions.ADMIN) is False
        assert child.has_permission(read_user, permissions.WRITE) is False
        assert child.has_permission(read_user, permissions.READ) is True
        # check redirect url
        assert '/contributors/' in res.location

    def test_group_copied_over_to_component_if_manager(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        write_user = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=permissions.WRITE)
        self.project.add_contributor(write_user, permissions=permissions.WRITE)
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, data=post_data, auth=write_user.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert non_admin in child.contributors
        assert self.user1 in child.contributors
        assert self.user2 in child.contributors
        assert write_user in child.contributors
        assert child.has_permission(non_admin, permissions.ADMIN) is False
        assert child.has_permission(non_admin, permissions.WRITE) is True
        assert child.has_permission(non_admin, permissions.READ) is True
        # Component creator gets admin
        assert child.has_permission(write_user, permissions.ADMIN) is True
        assert child.has_permission(write_user, permissions.WRITE) is True
        assert child.has_permission(write_user, permissions.READ) is True
        # check redirect url
        assert '/contributors/' in res.location

    def test_create_component_with_contributors_read(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=permissions.READ)
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, json=post_data, auth=non_admin.auth)
        assert res.status_code == 403

    def test_create_component_add_no_contributors(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        post_data = {'title': 'New Component With Contributors Title', 'category': ''}
        res = self.app.post(url, data=post_data, auth=self.user1.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert self.user1 in child.contributors
        assert self.user2 not in child.contributors
        # check redirect url
        assert '/contributors/' not in res.location

    def test_new_project_returns_serialized_node_data(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = res.json['newNode']
        assert node
        assert node['title'] == 'Im a real title'

    def test_description_works(self):
        payload = {
            'title': 'Im a real title',
            'description': 'I describe things!'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert node.description == 'I describe things!'

    def test_can_template(self):
        other_node = ProjectFactory(creator=self.creator)
        payload = {
            'title': 'Im a real title',
            'template': other_node._id
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert node.template_node == other_node

    def test_project_before_template_no_addons(self):
        project = ProjectFactory()
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert res.json['prompts'] == []

    def test_project_before_template_with_addons(self):
        project = ProjectWithAddonFactory(addon='box')
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert 'Box' in res.json['prompts']

    def test_project_new_from_template_non_user(self):
        project = ProjectFactory()
        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=None)
        assert res.status_code == 302
        res2 = self.app.resolve_redirect(res)
        assert res2.status_code == 308
        assert res2.request.path == '/login'

    def test_project_new_from_template_public_non_contributor(self):
        non_contributor = AuthUserFactory()
        project = ProjectFactory(is_public=True)
        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=non_contributor.auth)
        assert res.status_code == 201

    def test_project_new_from_template_contributor(self):
        contributor = AuthUserFactory()
        project = ProjectFactory(is_public=False)
        project.add_contributor(contributor)
        project.save()

        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=contributor.auth)
        assert res.status_code == 201
