# -*- coding: utf-8 -*-
import mock
from mock import call
import requests
from nose.tools import *  # noqa

from tests.base import OsfTestCase

import addons.weko.client as client

fake_weko_last_index_id = 10
fake_weko_host = 'http://localhost.weko.fake/'
fake_weko_collection_url = '{0}collection'.format(fake_weko_host)
fake_weko_servicedocument_url = "{0}servicedocument.php".format(fake_weko_host)

fake_weko_service_document_xml = """
<?xml version="1.0" encoding="utf-8"?>
<service xmlns:dcterms="http://purl.org/dc/terms/" xmlns="http://www.w3.org/2007/app" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:sword="http://purl.org/net/sword/">
  <sword:version>2</sword:version>
  <sword:verbose>false</sword:verbose>
  <sword:noOp>false</sword:noOp>
  <sword:maxUploadSize>512000</sword:maxUploadSize>
  <workspace>
    <atom:title>WEKO</atom:title>
    <collection href="{collection_url}">
      <atom:title>Repository Review</atom:title>
      <accept>application/zip</accept>
      <dcterms:abstract>This is the review repository.</dcterms:abstract>
      <sword:mediation>true</sword:mediation>
      <sword:treatment>Deposited items(zip) will be treated as WEKO import file which contains any WEKO contents information, and will be imported to WEKO.</sword:treatment>
      <sword:collectionPolicy>This collection accepts packages from any admin/moderator users on WEKO.</sword:collectionPolicy>
      <sword:formatNamespace>WEKO</sword:formatNamespace>
    </collection>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/metadata/dublin_core#">
      <rdf:Description rdf:about="{weko_host}?action=repository_oaiore&amp;indexId={last_index_id}">
        <dc:identifier>{last_index_id}</dc:identifier>
        <dc:title>fake project title</dc:title>
      </rdf:Description>
    </rdf:RDF>
  </workspace>
</service>
""".format(
    weko_host=fake_weko_host,
    collection_url=fake_weko_collection_url,
    last_index_id=fake_weko_last_index_id
).strip()

fake_weko_create_index_post_result_xml = """
<?xml version="1.0" encoding="utf-8"?>
<result></result>
""".strip()


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


mock_response_404 = MockResponse('404 not found', 404)


def mock_requests_get(url, **kwargs):
    if 'servicedocument.php' in url:
        return MockResponse(fake_weko_service_document_xml, 200)

    return mock_response_404


def mock_requests_post(url, **kwargs):
    if url == fake_weko_collection_url:
        return MockResponse(fake_weko_create_index_post_result_xml, 200)

    return mock_response_404


class TestWEKOClient(OsfTestCase):
    def setUp(self):
        self.host = fake_weko_host
        self.conn = client.connect_or_error(self.host)
        super(TestWEKOClient, self).setUp()

    def tearDown(self):
        super(TestWEKOClient, self).tearDown()

    @mock.patch('requests.get', side_effect=mock_requests_get)
    @mock.patch('requests.post', side_effect=mock_requests_post)
    def test_weko_create_index(self, get_req_mock, post_req_mock):
        index_id = client.create_index(self.conn)
        assert_equal(index_id, fake_weko_last_index_id + 1)
