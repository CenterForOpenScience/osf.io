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

    def test_rss_returns_valid_xml(self):
        ret = utils.elastic_to_rss('name', [], '*', 'http://website.web')
        parser = etree.XMLParser(dtd_validation=True)
        import pdb; pdb.set_trace()




# TODO Figure out a good way to test XML....
