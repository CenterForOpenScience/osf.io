# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

from framework.forms.utils import sanitize_payload
from framework.exceptions import SanitizeError

from website.project.model import MetaSchema
from website.project.model import ensure_schemas
from website.project.metadata.schemas import OSF_META_SCHEMAS

from tests.base import DbTestCase


class TestMetaData(DbTestCase):

    def test_ensure_schemas(self):

        # Should be zero MetaSchema records to begin with
        assert_equal(
            MetaSchema.find().count(),
            0
        )

        ensure_schemas()

        assert_equal(
            MetaSchema.find().count(),
            len(OSF_META_SCHEMAS)
        )

    def test_sanitize_clean(self):
        try:
            sanitize_payload({'foo': 'bar'})
        except SanitizeError:
            assert False

    def test_sanitize_clean_list(self):
        try:
            sanitize_payload({'foo': ['bar', 'baz']})
        except SanitizeError:
            assert False

    def test_sanitize_dirty_value(self):
        with assert_raises(SanitizeError):
            sanitize_payload({'foo': '<bar />'})

    def test_sanitize_dirty_list(self):
        with assert_raises(SanitizeError):
            sanitize_payload(({'foo': ['bar', '<baz />']}))

if __name__ == '__main__':
    unittest.main()
