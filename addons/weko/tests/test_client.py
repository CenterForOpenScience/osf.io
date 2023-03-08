# -*- coding: utf-8 -*-
import mock
from mock import call
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from addons.weko import client
from addons.weko.tests import utils


def mock_requests_get(url, **kwargs):
    if url == 'https://test.sample.nii.ac.jp/api/tree':
        return utils.MockResponse(utils.fake_weko_indices, 200)
    if url == 'https://test.sample.nii.ac.jp/api/index/?search_type=2&q=100':
        return utils.MockResponse(utils.fake_weko_items, 200)
    if url == 'https://test.sample.nii.ac.jp/api/records/1000':
        return utils.MockResponse(utils.fake_weko_item, 200)
    return utils.mock_response_404


class TestWEKOClient(OsfTestCase):
    def setUp(self):
        self.host = utils.fake_weko_host
        self.conn = client.Client(self.host)
        super(TestWEKOClient, self).setUp()

    def tearDown(self):
        super(TestWEKOClient, self).tearDown()

    @mock.patch('requests.get', side_effect=mock_requests_get)
    def test_weko_get_indices(self, get_req_mock):
        indices = self.conn.get_indices()
        assert_equal(len(indices), 1)
        assert_equal(indices[0].title, 'Sample Index')
        assert_equal(indices[0].identifier, 100)

    @mock.patch('requests.get', side_effect=mock_requests_get)
    def test_weko_get_index_by_id(self, get_req_mock):
        index = self.conn.get_index_by_id(100)
        assert_equal(index.title, 'Sample Index')
        assert_equal(index.identifier, 100)

        with assert_raises(ValueError):
            self.conn.get_index_by_id(101)

    @mock.patch('requests.get', side_effect=mock_requests_get)
    def test_weko_get_items(self, get_req_mock):
        index = self.conn.get_index_by_id(100)
        items = index.get_items()

        assert_equal(len(items), 1)
        assert_equal(items[0].title, 'Sample Item')
        assert_equal(items[0].identifier, 1000)

    @mock.patch('requests.get', side_effect=mock_requests_get)
    def test_weko_get_item_by_id(self, get_req_mock):
        index = self.conn.get_index_by_id(100)
        item = index.get_item_by_id(1000)

        assert_equal(item.title, 'Sample Item')
        assert_equal(item.identifier, 1000)
