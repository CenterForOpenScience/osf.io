from nose.tools import *  # noqa

import mock

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, RegistrationFactory

from website.project.model import Node
from website.settings import POPULAR_LINKS_NODE, POPULAR_LINKS_REGISTRATIONS, NEW_AND_NOTEWORTHY_LINKS_NODE

from scripts import populate_popular_projects_and_registrations as script


class TestPopulateNewAndNoteworthy(OsfTestCase):

    def setUp(self):
        super(TestPopulateNewAndNoteworthy, self).setUp()
        self.pop1 = ProjectFactory(is_public=True)
        self.pop2 = ProjectFactory(is_public=True)

        self.popreg1 = RegistrationFactory(is_public=True)
        self.popreg2 = RegistrationFactory(is_public=True)

    def tearDown(self):
        super(TestPopulateNewAndNoteworthy, self).tearDown()
        Node.remove()

    @mock.patch('website.project.utils.get_keen_activity')
    def test_populate_popular_nodes_and_registrations(self, mock_client):

        # only for setup, not used
        self.new_noteworthy_node = ProjectFactory()
        self.new_noteworthy_node._id = NEW_AND_NOTEWORTHY_LINKS_NODE
        self.new_noteworthy_node.save()

        self.popular_links_node = ProjectFactory()
        self.popular_links_node._id = POPULAR_LINKS_NODE
        self.popular_links_node.save()

        self.popular_links_registrations = ProjectFactory()
        self.popular_links_registrations._id = POPULAR_LINKS_REGISTRATIONS
        self.popular_links_registrations.save()

        popular_nodes = [self.pop1, self.pop2]
        popular_registrations = [self.popreg1, self.popreg2]

        node_pageviews = [
            {
                'result': 5,
                'node.id': self.pop1._id
            },
            {
                'result': 5,
                'node.id': self.pop2._id
            },
            {
                'result': 5,
                'node.id': self.popreg1._id
            },
            {
                'result': 5,
                'node.id': self.popreg2._id
            }
        ]

        node_visits = [
            {
                'result': 2,
                'node.id': self.pop1._id
            },
            {
                'result': 2,
                'node.id': self.pop2._id
            },
            {
                'result': 2,
                'node.id': self.popreg1._id
            },
            {
                'result': 2,
                'node.id': self.popreg2._id
            }
        ]

        mock_client.return_value = {'node_pageviews': node_pageviews, 'node_visits': node_visits}

        assert_equal(len(self.popular_links_node.nodes), 0)
        assert_equal(len(self.popular_links_registrations.nodes), 0)

        script.main(dry_run=False)

        self.popular_links_node.reload()
        self.popular_links_registrations.reload()

        assert_equal(len(self.popular_links_node.nodes), 2)
        assert_equal(len(self.popular_links_registrations.nodes), 2)

        assert_items_equal(
            popular_nodes,
            [pointer.node for pointer in self.popular_links_node.nodes]
        )
        assert_items_equal(
            popular_registrations,
            [pointer.node for pointer in self.popular_links_registrations.nodes]
        )
