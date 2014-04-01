# -*- coding: utf-8 -*-
import os
import unittest
from docutils.core import publish_parts
from nose.tools import *

from .__init__ import RstRenderer

here, _ = os.path.split(os.path.abspath(__file__))
f = open(os.path.join(here, 'fixtures/test.rst'), 'r')
string = f.read()
htmlstring = publish_parts(string, writer_name='html')['html_body']
f.close()



class TestRST(unittest.TestCase):
    def setUp(self):
        self.renderer = RstRenderer()

    # Test renderer
    def test_text_in_doc(self):
        assert_true('ReStructuredText (rst): plain text markup' in htmlstring)

    def test_for_unicode(self):
        assert_true(isinstance(htmlstring, unicode))

    def test_for_html_tags(self):
        rst = '<div'
        assert_true(rst in htmlstring)

    def test_for_bold(self):
        assert_true('<strong>bold</strong>' in htmlstring)

    def test_for_unicode_character(self):
        assert_true(u'\xfc' in htmlstring)
