from unittest import mock

from tests.base import OsfTestCase
from osf_tests.factories import ProjectFactory

from osf.models import Node

from scripts import populate_new_and_noteworthy_projects as script

NEW_AND_NOTEWORTHY_LINKS_NODE = 'nguid'


@mock.patch('scripts.populate_new_and_noteworthy_projects.NEW_AND_NOTEWORTHY_LINKS_NODE', NEW_AND_NOTEWORTHY_LINKS_NODE)
class TestPopulateNewAndNoteworthy(OsfTestCase):

    def setUp(self):
        super().setUp()

        self.new_and_noteworthy_links_node = ProjectFactory()
        self.new_and_noteworthy_links_node._id = NEW_AND_NOTEWORTHY_LINKS_NODE
        self.new_and_noteworthy_links_node.save()

        self.nn1 = ProjectFactory(is_public=True, title='Noteworthy Project Alpha')
        self.nn2 = ProjectFactory(is_public=True, title='Noteworthy Project Beta')
        self.nn3 = ProjectFactory(is_public=True, title='Noteworthy Project Gamma')
        self.nn4 = ProjectFactory(is_public=True, title='Noteworthy Project Delta')
        self.nn5 = ProjectFactory(is_public=True, title='Noteworthy Project Epsilon')

        self.all_ids = {self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id}

    def tearDown(self):
        super().tearDown()
        Node.objects.all().delete()

    def test_get_new_and_noteworthy_nodes(self):
        new_noteworthy = script.get_new_and_noteworthy_nodes(self.new_and_noteworthy_links_node)
        assert set(new_noteworthy) == self.all_ids

    def test_populate_new_and_noteworthy(self):
        assert self.new_and_noteworthy_links_node._nodes.count() == 0

        script.main(dry_run=False)
        self.new_and_noteworthy_links_node.reload()

        assert self.new_and_noteworthy_links_node._nodes.count() == 5

        script.main(dry_run=False)

        self.new_and_noteworthy_links_node.reload()

        # new_and_noteworthy_node_links = {pointer.node._id for pointer in self.new_and_noteworthy_links_node.nodes}
        new_and_noteworthy_node_links = self.new_and_noteworthy_links_node._nodes.all().values_list('guids___id', flat=True)

        assert set(new_and_noteworthy_node_links) == self.all_ids
