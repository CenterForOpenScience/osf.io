import pytest
from lxml import html
from framework.auth import Auth
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    NodeFactory,
    ProjectFactory,
    UserFactory,
)
from tests.base import (
    OsfTestCase,
)
from tests.utils import capture_notifications
from website.project.views.node import abbrev_authors
from website.util import web_url_for

pytestmark = pytest.mark.django_db

@pytest.mark.enable_bookmark_creation
class TestPointerViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _make_pointer_only_user_can_see(self, user, project, save=False):
        node = ProjectFactory(creator=user)
        project.add_pointer(node, auth=Auth(user=user), save=save)

    def test_pointer_list_write_contributor_can_remove_private_component_entry(self):
        """Ensure that write contributors see the button to delete a pointer,
            even if they cannot see what it is pointing at"""
        url = web_url_for('view_project', pid=self.project._id)
        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS)

        self._make_pointer_only_user_can_see(user2, self.project)
        self.project.save()

        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == 200

        has_controls = html.fromstring(res.text).xpath('//li[@node_id]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert has_controls

    def test_pointer_list_write_contributor_can_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        for i in range(3):
            self.project.add_pointer(ProjectFactory(creator=self.user),
                                     auth=Auth(user=self.user))
        self.project.save()

        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == 200
        has_controls = html.fromstring(res.text).xpath(
            '//div[@node_id]//i[contains(@class, "remove-pointer")]'
        )
        assert len(has_controls) == 3

    def test_pointer_list_read_contributor_cannot_remove_private_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)
        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=permissions.READ)

        self._make_pointer_only_user_can_see(user2, self.project)
        self.project.save()

        res = self.app.get(url, auth=user2.auth, follow_redirects=True)
        assert res.status_code == 200

        pointer_nodes = html.fromstring(res.text).xpath('//div[@node_id]')
        has_controls = html.fromstring(res.text).xpath('//div[@node_id]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert len(pointer_nodes) == 1
        assert not has_controls

    def test_pointer_list_read_contributor_cannot_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        self.project.add_pointer(ProjectFactory(creator=self.user,
                                                is_public=True),
                                 auth=Auth(user=self.user))

        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=permissions.READ)
        self.project.save()

        res = self.app.get(url, auth=user2.auth, follow_redirects=True)
        assert res.status_code == 200

        pointer_nodes = html.fromstring(res.text).xpath('//div[@node_id]')
        has_controls = html.fromstring(res.text).xpath(
            '//li[@node_id]//i[contains(@class, "remove-pointer")]')
        assert len(pointer_nodes) == 1
        assert len(has_controls) == 0

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1109
    def test_get_pointed_excludes_folders(self):
        pointer_project = ProjectFactory(is_public=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=self.user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        # Project is in an organizer collection
        collection = CollectionFactory(creator=pointed_project.creator)
        collection.collect_object(pointed_project, self.user)

        url = pointed_project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        # pointer_project's id is included in response, but folder's id is not
        pointer_ids = [each['id'] for each in res.json['pointed']]
        assert pointer_project._id in pointer_ids
        assert collection._id not in pointer_ids

    def test_add_pointers(self):

        url = self.project.api_url + 'pointer/'
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post(
            url,
            json={'nodeIds': node_ids},
            auth=self.user.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert self.project.nodes_active.count() == 5

    def test_add_the_same_pointer_more_than_once(self):
        url = self.project.api_url + 'pointer/'
        double_node = NodeFactory()

        self.app.post(
            url,
            json={'nodeIds': [double_node._id]},
            auth=self.user.auth,
        )
        res = self.app.post(
            url,
            json={'nodeIds': [double_node._id]},
            auth=self.user.auth,
        )
        assert res.status_code == 400

    def test_add_pointers_no_user_logg_in(self):

        url = self.project.api_url_for('add_pointers')
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        res = self.app.post(
            url,
            json={'nodeIds': node_ids},
            auth=None,
        )

        assert res.status_code == 401

    def test_add_pointers_public_non_contributor(self):

        project2 = ProjectFactory()
        project2.set_privacy('public')
        project2.save()

        url = self.project.api_url_for('add_pointers')

        self.app.post(
            url,
            json={'nodeIds': [project2._id]},
            auth=self.user.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert self.project.nodes_active.count() == 1

    def test_add_pointers_contributor(self):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2)
        self.project.save()

        url = self.project.api_url_for('add_pointers')
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post(
            url,
            json={'nodeIds': node_ids},
            auth=user2.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert self.project.linked_nodes.count() == 5

    def test_add_pointers_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.post(url, json={}, auth=self.user.auth)
        assert res.status_code == 400


    def test_remove_pointer(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.delete(
            url,
            json={'pointerId': pointer.node._id},
            auth=self.user.auth,
        )
        self.project.reload()
        assert len(list(self.project.nodes)) == 0

    def test_remove_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete(url, json={}, auth=self.user.auth)
        assert res.status_code == 400

    def test_remove_pointer_not_found(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete(
            url,
            json={'pointerId': None},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_remove_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete(
            url,
            json={'pointerId': 'somefakeid'},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_forking_pointer_works(self):
        url = self.project.api_url + 'pointer/fork/'
        linked_node = NodeFactory(creator=self.user)
        pointer = self.project.add_pointer(linked_node, auth=self.consolidate_auth)
        assert linked_node.id == pointer.child.id
        with capture_notifications():
            res = self.app.post(url, json={'nodeId': pointer.child._id}, auth=self.user.auth)
        assert res.status_code == 201
        assert 'node' in res.json['data']
        fork = res.json['data']['node']
        assert fork['title'] == f'Fork of {linked_node.title}'

    def test_fork_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post(url, json={}, auth=self.user.auth,
                                 )
        assert res.status_code == 400

    def test_fork_pointer_not_found(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post(
            url,
            json={'nodeId': None},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_fork_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post(
            url,
            json={'nodeId': 'somefakeid'},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_before_register_with_pointer(self):
        # Assert that link warning appears in before register callback.
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert len(prompts) == 1

    def test_before_fork_with_pointer(self):
        """Assert that link warning appears in before fork callback."""
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'These links will be copied into your registration,' in prompt
        ]
        assert len(prompts) == 1

    def test_before_register_no_pointer(self):
        """Assert that link warning does not appear in before register callback."""
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert len(prompts) == 0

    def test_before_fork_no_pointer(self):
        """Assert that link warning does not appear in before fork callback."""
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert len(prompts) == 0

    def test_get_pointed(self):
        pointing_node = ProjectFactory(creator=self.user)
        pointing_node.add_pointer(self.project, auth=Auth(self.user))
        url = self.project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        pointed = res.json['pointed']
        assert len(pointed) == 1
        assert pointed[0]['url'] == pointing_node.url
        assert pointed[0]['title'] == pointing_node.title
        assert pointed[0]['authorShort'] == abbrev_authors(pointing_node)

    def test_get_pointed_private(self):
        secret_user = UserFactory()
        pointing_node = ProjectFactory(creator=secret_user)
        pointing_node.add_pointer(self.project, auth=Auth(secret_user))
        url = self.project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        pointed = res.json['pointed']
        assert len(pointed) == 1
        assert pointed[0]['url'] is None
        assert pointed[0]['title'] == 'Private Component'
        assert pointed[0]['authorShort'] == 'Private Author(s)'

    def test_can_template_project_linked_to_each_other(self):
        project2 = ProjectFactory(creator=self.user)
        self.project.add_pointer(project2, auth=Auth(user=self.user))
        with capture_notifications():
            template = self.project.use_as_template(auth=Auth(user=self.user))

        assert template
        assert template.title == 'Templated from ' + self.project.title
        assert project2 not in template.linked_nodes
