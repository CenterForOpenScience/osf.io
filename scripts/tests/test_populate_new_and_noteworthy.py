from nose.tools import *  # noqa

import json
import httpretty
import datetime, dateutil

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory

from website.project.model import Auth, Node
from website.settings import POPULAR_LINKS_NODE, NEW_AND_NOTEWORTHY_LINKS_NODE

from scripts import populate_new_and_noteworthy_projects as script


class TestPopulateNewAndNoteworthy(OsfTestCase):

    def setUp(self):
        super(TestPopulateNewAndNoteworthy, self).setUp()
        self.pop1 = ProjectFactory()
        self.pop2 = ProjectFactory()
        self.pop3 = ProjectFactory()
        self.pop4 = ProjectFactory()
        self.pop5 = ProjectFactory()

        self.nn1 = ProjectFactory(is_public=True)
        self.nn2 = ProjectFactory(is_public=True)
        self.nn3 = ProjectFactory(is_public=True)
        self.nn4 = ProjectFactory(is_public=True)
        self.nn5 = ProjectFactory(is_public=True)

        self.user = UserFactory()

        today = datetime.datetime.now()
        self.last_month = (today - dateutil.relativedelta.relativedelta(months=1)).isoformat()

        popular_json = {"popular_node_ids": [self.pop1._id, self.pop2._id, self.pop3._id, self.pop4._id, self.pop5._id]}
        self.popular_json_body = json.dumps(popular_json)

    def tearDown(self):
        super(TestPopulateNewAndNoteworthy, self).tearDown()
        Node.remove()

    def test_get_new_and_noteworthy_nodes(self):
        new_noteworthy = script.get_new_and_noteworthy_nodes()
        assert_equal(set(new_noteworthy), {self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id})

    def test_populate_new_and_noteworthy(self):
        self.popular_links_node = ProjectFactory(creator=self.user)
        self.popular_links_node._id = POPULAR_LINKS_NODE
        self.popular_links_node.save()
        self.new_and_noteworthy_links_node = ProjectFactory()
        self.new_and_noteworthy_links_node._id = NEW_AND_NOTEWORTHY_LINKS_NODE
        self.new_and_noteworthy_links_node.save()

        popular_nodes = [self.pop1, self.pop2, self.pop3, self.pop4, self.pop5]

        for node in popular_nodes:
            self.popular_links_node.add_pointer(node, auth=Auth(self.user), save=True)

        assert_equal(len(self.popular_links_node.nodes), 5)
        assert_equal(len(self.new_and_noteworthy_links_node.nodes), 0)


        script.main(dry_run=False)
        self.popular_links_node.reload()
        self.new_and_noteworthy_links_node.reload()

        assert_equal(len(self.popular_links_node.nodes), 0)  # verifies remove pointer is working
        assert_equal(len(self.new_and_noteworthy_links_node.nodes), 5)

        script.main(dry_run=False)

        self.popular_links_node.reload()
        self.new_and_noteworthy_links_node.reload()

        popular_node_links = [pointer.node._id for pointer in self.popular_links_node.nodes]
        assert_equal(popular_node_links, [])

        new_and_noteworthy_node_links = {pointer.node._id for pointer in self.new_and_noteworthy_links_node.nodes}

        assert_equal(set(new_and_noteworthy_node_links), {self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id})
