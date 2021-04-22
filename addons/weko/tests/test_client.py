# -*- coding: utf-8 -*-
import datetime

import mock
from mock import call
import requests
from nose.tools import *  # noqa

from lxml import etree
import re

from tests.base import OsfTestCase

import addons.weko.client as client

fake_weko_last_index_id = 10
fake_weko_host = 'http://localhost.weko.fake/'
fake_weko_collection_url = '{0}collection'.format(fake_weko_host)
fake_weko_servicedocument_url = '{0}servicedocument.php'.format(fake_weko_host)

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

fake_weko_item_item_type = {
    'mapping_info': 'Journal Article', 'basic_attributes': [
        {'type': 'title', 'columns': [{'column_name': u'タイトル', 'column_id': 'value'}]},
        {'type': 'titleInEnglish', 'columns': [{'column_name': u'タイトル(英)', 'column_id': 'value'}]},
        {'type': 'language', 'columns': [{'column_name': u'言語', 'column_id': 'value'}]},
        {'type': 'keywords', 'columns': [{'column_name': u'キーワード', 'column_id': 'value'}]},
        {'type': 'keywordsInEnglish', 'columns': [{'column_name': u'キーワード(英)', 'column_id': 'value'}]},
        {'type': 'publicationDate', 'columns': [{'column_name': u'公開日', 'column_id': 'value'}]}
    ],
    'additional_attributes': [
        {'required': 'false', 'dublin_core_mapping': 'title', 'name': u'その他（別言語等）のタイトル',
         'delimiters': '|', 'junii2_mapping': 'alternative', 'allowmultipleinput': 'true',
         'specifynewline': 'false', 'listing': 'false', 'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'creator', 'name': u'著者', 'delimiters': '|',
         'junii2_mapping': 'creator', 'allowmultipleinput': 'true', 'specifynewline': 'true', 'listing': 'true',
         'hidden': 'false', 'type': 'name', 'display_lang_type': 'japanese', 'isfamilygivenconnected': 'true'},
        {'required': 'false', 'dublin_core_mapping': '', 'name': u'著者（英）', 'delimiters': '|', 'junii2_mapping': '',
         'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false', 'hidden': 'false', 'type': 'name',
         'display_lang_type': 'english', 'isfamilygivenconnected': 'true'},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': u'著者ID', 'delimiters': '|',
         'junii2_mapping': 'identifier', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'description', 'name': u'抄録', 'delimiters': '|',
         'junii2_mapping': 'description', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'textarea', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'description', 'name': u'内容記述', 'delimiters': '|',
         'junii2_mapping': 'description', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'textarea', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': u'書誌情報', 'delimiters': '|',
         'junii2_mapping': 'jtitle,volume,issue,spage,epage,dateofissued', 'allowmultipleinput': 'false',
         'isstartendpageconnected': 'false', 'specifynewline': 'false', 'listing': 'true', 'hidden': 'false',
         'type': 'biblioinfo', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'publisher', 'name': u'出版者', 'delimiters': '|',
         'junii2_mapping': 'publisher', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': 'ISSN', 'delimiters': '|',
         'junii2_mapping': 'issn', 'allowmultipleinput': 'false', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': 'ISBN', 'delimiters': '|',
         'junii2_mapping': 'isbn', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': u'書誌レコードID', 'delimiters': '|',
         'junii2_mapping': 'NCID', 'allowmultipleinput': 'false', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': u'論文ID（NAID）', 'delimiters': '|',
         'junii2_mapping': 'NAID', 'allowmultipleinput': 'false', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'relation', 'name': u'PubMed番号', 'delimiters': '|',
         'junii2_mapping': 'pmid', 'allowmultipleinput': 'false', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'relation', 'name': 'DOI', 'delimiters': '|',
         'junii2_mapping': 'doi', 'allowmultipleinput': 'false', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'rights', 'name': u'権利', 'delimiters': '|',
         'junii2_mapping': 'rights', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'source', 'name': u'情報源', 'delimiters': '|',
         'junii2_mapping': 'source', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'source', 'name': u'関連サイト', 'delimiters': '|',
         'junii2_mapping': 'source', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'link', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'relation', 'name': u'他の資源との関係', 'delimiters': '|',
         'junii2_mapping': 'relation', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'format', 'name': u'フォーマット', 'delimiters': '|',
         'junii2_mapping': 'format', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': '', 'name': u'著者版フラグ', 'delimiters': '|',
         'junii2_mapping': 'textversion', 'allowmultipleinput': 'false',
         'candidates': ['author', 'publisher', 'ETD', 'none'], 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'pulldownmenu', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'subject', 'name': u'日本十進分類法', 'delimiters': '|',
         'junii2_mapping': 'NDC', 'allowmultipleinput': 'true', 'specifynewline': 'false', 'listing': 'false',
         'hidden': 'false', 'type': 'text', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': 'identifier', 'name': u'コンテンツ本体', 'delimiters': '|',
         'junii2_mapping': 'fullTextURL', 'allowmultipleinput': 'true', 'displaytype': 'detail',
         'specifynewline': 'true', 'listing': 'true', 'hidden': 'false', 'type': 'file', 'display_lang_type': ''},
        {'required': 'false', 'dublin_core_mapping': '', 'name': u'見出し', 'delimiters': '|', 'junii2_mapping': '',
         'allowmultipleinput': 'false', 'specifynewline': 'false', 'listing': 'false', 'hidden': 'false',
         'type': 'heading', 'display_lang_type': ''}
    ],
    'name': u'学術雑誌論文 / Journal Article'
}
fake_weko_item_internal_item_type_id = 10001
fake_weko_item_uploaded_filenames = [u'test_file.pdf']
fake_weko_item_uploaded_filenames2 = [u'test_file.PDF']
fake_weko_item_title = u'test_title'
fake_weko_item_title_en = u'test_title'
fake_weko_item_contributors = [{'name': u'test_user', 'family': u''}]

fake_expected_create_import_xml_template = u"""
<export>
    <repository_item item_id="1" item_no="1" revision_no="0" prev_revision_no="0" item_type_id="10001"
                     title="test_title" title_english="test_title" language="ja" review_status="0" review_date=""
                     shown_status="1" shown_date="{date}" reject_status="0" reject_date="" reject_reason=""
                     search_key="" search_key_english="" remark=""/>
    <repository_item_type item_type_id="10001" item_type_name="学術雑誌論文 / Journal Article"
                          item_type_short_name="学術雑誌論文 / Journal Article" mapping_info="Journal Article"
                          explanation="default item type"/>
    <repository_item_attr_type item_type_id="10001" attribute_id="1" show_order="1" attribute_name="その他（別言語等）のタイトル"
                               attribute_short_name="その他（別言語等）のタイトル" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="title"
                               junii2_mapping="alternative" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="2" show_order="2" attribute_name="著者"
                               attribute_short_name="著者" input_type="name" is_required="0" plural_enable="1"
                               line_feed_enable="1" list_view_enable="1" hidden="0" dublin_core_mapping="creator"
                               junii2_mapping="creator" display_lang_type="japanese"/>
    <repository_personal_name item_type_id="10001" attribute_id="2" item_no="1" personal_name_no="1" author_id="1"
                              family="" family_ruby="" name="test_user" name_ruby="test_user" e_mail_address=""
                              prefix_name="" suffix="" item_id="1"/>
    <repository_item_attr_type item_type_id="10001" attribute_id="3" show_order="3" attribute_name="著者（英）"
                               attribute_short_name="著者（英）" input_type="name" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping=""
                               junii2_mapping="" display_lang_type="english"/>
    <repository_item_attr_type item_type_id="10001" attribute_id="4" show_order="4" attribute_name="著者ID"
                               attribute_short_name="著者ID" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="identifier" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="5" show_order="5" attribute_name="抄録"
                               attribute_short_name="抄録" input_type="textarea" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="description"
                               junii2_mapping="description" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="6" show_order="6" attribute_name="内容記述"
                               attribute_short_name="内容記述" input_type="textarea" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="description"
                               junii2_mapping="description" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="7" show_order="7" attribute_name="書誌情報"
                               attribute_short_name="書誌情報" input_type="biblio_info" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="1" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="jtitle,volume,issue,spage,epage,dateofissued" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="8" show_order="8" attribute_name="出版者"
                               attribute_short_name="出版者" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="publisher"
                               junii2_mapping="publisher" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="9" show_order="9" attribute_name="ISSN"
                               attribute_short_name="ISSN" input_type="text" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="issn" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="10" show_order="10" attribute_name="ISBN"
                               attribute_short_name="ISBN" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="isbn" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="11" show_order="11" attribute_name="書誌レコードID"
                               attribute_short_name="書誌レコードID" input_type="text" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="NCID" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="12" show_order="12" attribute_name="論文ID（NAID）"
                               attribute_short_name="論文ID（NAID）" input_type="text" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="NAID" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="13" show_order="13" attribute_name="PubMed番号"
                               attribute_short_name="PubMed番号" input_type="text" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="relation"
                               junii2_mapping="pmid" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="14" show_order="14" attribute_name="DOI"
                               attribute_short_name="DOI" input_type="text" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="relation"
                               junii2_mapping="doi" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="15" show_order="15" attribute_name="権利"
                               attribute_short_name="権利" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="rights"
                               junii2_mapping="rights" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="16" show_order="16" attribute_name="情報源"
                               attribute_short_name="情報源" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="source"
                               junii2_mapping="source" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="17" show_order="17" attribute_name="関連サイト"
                               attribute_short_name="関連サイト" input_type="link" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="source"
                               junii2_mapping="source" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="18" show_order="18" attribute_name="他の資源との関係"
                               attribute_short_name="他の資源との関係" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="relation"
                               junii2_mapping="relation" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="19" show_order="19" attribute_name="フォーマット"
                               attribute_short_name="フォーマット" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="format"
                               junii2_mapping="format" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="20" show_order="20" attribute_name="著者版フラグ"
                               attribute_short_name="著者版フラグ" input_type="select" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping=""
                               junii2_mapping="textversion" display_lang_type=""/>
    <repository_item_attr_candidate item_type_id="10001" attribute_id="20" candidate_no="1" candidate_value="author"
                                    candidate_short_value="author"/>
    <repository_item_attr_candidate item_type_id="10001" attribute_id="20" candidate_no="2" candidate_value="publisher"
                                    candidate_short_value="publisher"/>
    <repository_item_attr_candidate item_type_id="10001" attribute_id="20" candidate_no="3" candidate_value="ETD"
                                    candidate_short_value="ETD"/>
    <repository_item_attr_candidate item_type_id="10001" attribute_id="20" candidate_no="4" candidate_value="none"
                                    candidate_short_value="none"/>
    <repository_item_attr_type item_type_id="10001" attribute_id="21" show_order="21" attribute_name="日本十進分類法"
                               attribute_short_name="日本十進分類法" input_type="text" is_required="0" plural_enable="1"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping="subject"
                               junii2_mapping="NDC" display_lang_type=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="22" show_order="22" attribute_name="コンテンツ本体"
                               attribute_short_name="コンテンツ本体" input_type="file" is_required="0" plural_enable="1"
                               line_feed_enable="1" list_view_enable="1" hidden="0" dublin_core_mapping="identifier"
                               junii2_mapping="fullTextURL" display_lang_type=""/>
    <repository_file item_type_id="10001" attribute_id="22" item_no="1" file_no="1" file_name="{file_name}"
                     display_name="{display_name}" display_type="0" mime_type="{mime_type}" extension="{extension}"
                     license_id="0" license_notation="" pub_date="{date}" item_id="1" browsing_flag="0"
                     cover_created_flag="0"/>
    <repository_license_master license_id="0" license_notation=""/>
    <repository_item_attr_type item_type_id="10001" attribute_id="23" show_order="23" attribute_name="見出し"
                               attribute_short_name="見出し" input_type="heading" is_required="0" plural_enable="0"
                               line_feed_enable="0" list_view_enable="0" hidden="0" dublin_core_mapping=""
                               junii2_mapping="" display_lang_type=""/>
</export>
"""
fake_expected_create_import_xml_template = re.sub(r'\s+', ' ', fake_expected_create_import_xml_template)
fake_expected_create_import_xml_template = fake_expected_create_import_xml_template.strip().replace('> <', '><')
fake_expected_create_import_xml = fake_expected_create_import_xml_template.format(
    file_name='test_file.pdf',
    display_name='test_file',
    mime_type='application/pdf',
    extension='pdf',
    date=datetime.datetime.now().strftime('%Y-%m-%d')
)
fake_expected_create_import_xml2 = fake_expected_create_import_xml_template.format(
    file_name='test_file.PDF',
    display_name='test_file',
    mime_type='application/pdf',
    extension='pdf',
    date=datetime.datetime.now().strftime('%Y-%m-%d')
)


def etree_to_dict(t):
    d = {t.tag: list(map(etree_to_dict, t.iterchildren()))}
    d.update(('@' + k, v) for k, v in t.attrib.iteritems())
    d['text'] = t.text
    return d


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content.encode('utf8')
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

    def test_weko_create_import_xml(self):
        res = client.create_import_xml(fake_weko_item_item_type, fake_weko_item_internal_item_type_id,
                                       fake_weko_item_uploaded_filenames, fake_weko_item_title,
                                       fake_weko_item_title_en, fake_weko_item_contributors)
        assert(etree_to_dict(res), etree_to_dict(etree.XML(fake_expected_create_import_xml)))

    def test_weko_create_import_xml_with_upper_ext(self):
        res = client.create_import_xml(fake_weko_item_item_type, fake_weko_item_internal_item_type_id,
                                       fake_weko_item_uploaded_filenames2, fake_weko_item_title,
                                       fake_weko_item_title_en, fake_weko_item_contributors)
        assert(etree_to_dict(res), etree_to_dict(etree.XML(fake_expected_create_import_xml2)))
