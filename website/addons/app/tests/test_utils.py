# -*- coding: utf-8 -*-
import mock
import unittest
from nose.tools import *  # noqa (PEP8 asserts)

from lxml import etree

from website.addons.app import utils



class TestUtils(unittest.TestCase):

    def test_args_to_query(self):
        ret = utils.args_to_query('*')

        assert_equal(ret['from'], 0)
        assert_equal(ret['size'], 250)
        assert_equal(ret['query']['query_string']['query'], '*')

    def test_args_to_query_limits(self):
        ret = utils.args_to_query('*', size=1000000000)

        assert_equal(ret['size'], 1000)

    def test_args_to_query_casts(self):
        ret = utils.args_to_query('*', size='horse', start='40')

        assert_equal(ret['from'], 40)
        assert_equal(ret['size'], 250)

    def test_args_to_query_negatives(self):
        ret = utils.args_to_query('*', size=-90, start=-78)

        assert_equal(ret['from'], 78)
        assert_equal(ret['size'], 90)

    def test_args_to_query(self):
        q = 'asdlkfhaewniaw;eln'

        ret = utils.args_to_query(q)

        assert_equal(ret['from'], 0)
        assert_equal(ret['size'], 250)
        assert_equal(ret['query']['query_string']['query'], q)

    def test_e_to_rss(self):
        ret = utils.elastic_to_rss('name', [], '*', 'ccreeeeeeeeed')
        assert_true(isinstance(ret, str))
        assert_in('name', ret)
        assert_in('All', ret)
        assert_in('ccreeeeeeeeed', ret)

    def test_rss_returns_xml(self):
        ret = utils.elastic_to_rss('scrapi', [], '*', 'http://website.web')
        xml = etree.fromstring(ret)
        assert_true(isinstance(xml, etree._Element))

    def test_rss_items(self):
        ret = utils.elastic_to_rss('scrapi', [{'id': {'serviceID': '1234', 'url': 'www.url.wow'}, 'dateUpdated': '2013-02-27'}], '*', 'site')
        xml = etree.fromstring(ret)
        service_id = xml.xpath('//guid/node()')[0]
        link = xml.xpath('//item/link/node()')[0]
        pubDate = xml.xpath('//pubDate/node()')[0]
        assert_equal(service_id, '1234')
        assert_equal(link, 'www.url.wow')
        assert_equal(pubDate, 'Wed, 27 Feb 2013 00:00:00 GMT')

    def test_resourcelist_is_xml(self):
        ret = utils.elastic_to_resourcelist('scrapi', [{'id': {'url': 'www.url.wow'}, 'dateUpdated': '2013-02-27'}], '*')
        xml = etree.fromstring(ret)
        assert_true(isinstance(xml, etree._Element))

    def test_changelist_is_xml(self):
        ret = utils.elastic_to_changelist('scrapi', [{'id': {'url': 'www.url.wow'}, 'dateUpdated': '2013-02-27'}], '*')
        xml = etree.fromstring(ret)
        assert_true(isinstance(xml, etree._Element))

    def test_capabilitylist_is_xml(self):
        ret = utils.generate_capabilitylist('resourcelist.io' , 'changelist.io')
        xml = etree.fromstring(ret)
        assert_true(isinstance(xml, etree._Element))


# TODO Figure out a good way to test XML....
