from website.models import Node
from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, NodeFactory
from scripts.migrate_registration_and_fork_log import (
    get_parent, get_all_parents
)


class TestMigrateLogs(OsfTestCase):

    def tearDown(self):
        OsfTestCase.tearDown(self)
        Node.remove()

    def test_get_parent(self):
        user = UserFactory()
        auth = Auth(user=user)
        project1 = ProjectFactory(creator=user)
        project2 = project1.fork_node(auth=auth)
        forked_from = get_parent(project2)

        assert forked_from is project1

        project3 = project2.register_node(schema=None, auth=auth, template="foo", data="bar")
        registered_from = get_parent(project3)

        assert registered_from is project2

    def test_get_all_parents(self):
        user = UserFactory()
        auth = Auth(user=user)
        project1 = ProjectFactory(creator=user)
        project2 = project1.fork_node(auth=auth)
        project3 = project2.register_node(schema=None, auth=auth, template="foo", data="bar")
        parent_list = get_all_parents(project3)

        assert len(parent_list) is 2
        assert project1 in parent_list
        assert project2 in parent_list