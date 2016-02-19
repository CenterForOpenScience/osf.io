from nose.tools import *  # noqa

import json
import httpretty
import datetime, dateutil

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

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

        self.nn1 = ProjectFactory()
        self.nn2 = ProjectFactory()
        self.nn3 = ProjectFactory()
        self.nn4 = ProjectFactory()
        self.nn5 = ProjectFactory()

        today = datetime.datetime.now()
        self.last_month = (today - dateutil.relativedelta.relativedelta(months=1)).isoformat()

        popular_json = {"popular_node_ids": [self.pop1._id, self.pop2._id, self.pop3._id, self.pop4._id, self.pop5._id]}
        self.popular_json_body = json.dumps(popular_json)

        new_and_noteworthy_json = {"data": [
            {"id": self.nn1._id,
            "relationships": {
                "logs": {
                    "links": {"related": {"href": "http://localhost:8000/v2/nodes/8cmfw/logs/","meta": {"count": 5}}}}}},
            {"id": self.nn2._id,
            "relationships": {
                "logs": {
                    "links": {"related": {"href": "http://localhost:8000/v2/nodes/8cmfw/logs/","meta": {"count": 4}}}}}},
            {"id": self.nn3._id,
            "relationships": {
                "logs": {
                    "links": {"related": {"href": "http://localhost:8000/v2/nodes/8cmfw/logs/","meta": {"count": 3}}}}}},
            {"id": self.nn4._id,
                "relationships": {
                "logs": {
                    "links": {"related": {"href": "http://localhost:8000/v2/nodes/8cmfw/logs/","meta": {"count": 2}}}}}},
            {"id": self.nn5._id,
            "relationships": {
                "logs": {
                    "links": {"related": {"href": "http://localhost:8000/v2/nodes/8cmfw/logs/","meta": {"count": 1}}}}}},
            ]
        }
        self.new_noteworthy_json_body = json.dumps(new_and_noteworthy_json)

    def test_retrieve_data(self):
        base = script.get_api_base_path()
        httpretty.register_uri(httpretty.GET, base, status=200, body=self.popular_json_body, content_type='application/vnd.api+json')
        response = script.retrieve_data(base)
        assert_equal(response['popular_node_ids'], [self.pop1._id, self.pop2._id, self.pop3._id, self.pop4._id, self.pop5._id])

    def test_get_popular_nodes(self):
        url = script.get_api_base_path() + 'api/v1/explore/activity/popular/raw/'
        httpretty.register_uri(httpretty.GET, url, status=200, body=self.popular_json_body, content_type='application/vnd.api+json')
        response = script.get_popular_nodes()
        assert_equal(response['popular_node_ids'], [self.pop1._id, self.pop2._id, self.pop3._id, self.pop4._id, self.pop5._id])

    def test_get_new_and_noteworthy_nodes(self):
        base = script.get_apiv2_base_path()
        url = base + 'v2/nodes/?sort=-date_created&page[size]=1000&related_counts=True&filter[date_created][gt]={}'.format(self.last_month)
        httpretty.register_uri(httpretty.GET, url, status=200, body=self.new_noteworthy_json_body, content_type='application/vnd.api+json')
        new_noteworthy = script.get_new_and_noteworthy_nodes()
        assert_equal(new_noteworthy, [self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id])

    def test_populate_new_and_noteworthy(self):
        self.popular_links_node = ProjectFactory()
        self.popular_links_node._id = POPULAR_LINKS_NODE
        self.popular_links_node.save()
        self.new_and_noteworthy_links_node = ProjectFactory()
        self.new_and_noteworthy_links_node._id = NEW_AND_NOTEWORTHY_LINKS_NODE
        self.new_and_noteworthy_links_node.save()

        popular_url = script.get_api_base_path() + 'api/v1/explore/activity/popular/raw/'
        httpretty.register_uri(httpretty.GET, popular_url, status=200, body=self.popular_json_body, content_type='application/vnd.api+json')
        new_noteworthy_url = script.get_apiv2_base_path() + 'v2/nodes/?sort=-date_created&page[size]=1000&related_counts=True&filter[date_created][gt]={}'.format(self.last_month)
        httpretty.register_uri(httpretty.GET, new_noteworthy_url, status=200, body=self.new_noteworthy_json_body, content_type='application/vnd.api+json')

        script.main(dry_run=False)

        self.popular_links_node.reload()
        self.new_and_noteworthy_links_node.reload()

        popular_node_links = {pointer.node._id for pointer in self.popular_links_node.nodes}
        assert_equal(popular_node_links, {self.pop1._id, self.pop2._id, self.pop3._id, self.pop4._id, self.pop5._id})

        new_and_noteworthy_node_links = {pointer.node._id for pointer in self.new_and_noteworthy_links_node.nodes}
        assert_equal(new_and_noteworthy_node_links, {self.nn1._id, self.nn2._id, self.nn3._id, self.nn4._id, self.nn5._id})




