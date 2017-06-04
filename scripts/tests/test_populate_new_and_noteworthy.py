from nose.tools import *  # noqa

import mock

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.project.model import Node
from website.settings import NEW_AND_NOTEWORTHY_LINKS_NODE

from scripts import populate_new_and_noteworthy_projects as script


class TestPopulateNewAndNoteworthy(OsfTestCase):

    def setUp(self):
        super(TestPopulateNewAndNoteworthy, self).setUp()

        self.nn1 = ProjectFactory(is_public=True)
        self.nn2 = ProjectFactory(is_public=True)
        self.nn3 = ProjectFactory(is_public=True)
        self.nn4 = ProjectFactory(is_public=True)
        self.nn5 = ProjectFactory(is_public=True)

    def tearDown(self):
        super(TestPopulateNewAndNoteworthy, self).tearDown()
        Node.remove()

    def test_get_new_and_noteworthy_nodes(self):
        new_noteworthy = script.get_new_and_noteworthy_nodes()
        assert_equal(set(new_noteworthy), {self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id})

    def test_populate_new_and_noteworthy(self):

        self.new_and_noteworthy_links_node = ProjectFactory()
        self.new_and_noteworthy_links_node._id = NEW_AND_NOTEWORTHY_LINKS_NODE
        self.new_and_noteworthy_links_node.save()

        assert_equal(len(self.new_and_noteworthy_links_node.nodes), 0)

        script.main(dry_run=False)
        self.new_and_noteworthy_links_node.reload()

        assert_equal(len(self.new_and_noteworthy_links_node.nodes), 5)

        script.main(dry_run=False)

        self.new_and_noteworthy_links_node.reload()

        new_and_noteworthy_node_links = {pointer.node._id for pointer in self.new_and_noteworthy_links_node.nodes}

        assert_equal(set(new_and_noteworthy_node_links), {self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id})
