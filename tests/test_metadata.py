# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

from framework.forms.utils import process_payload

from website.project.model import MetaSchema
from website.project.model import ensure_schemas
from website.project.metadata.schemas import OSF_META_SCHEMAS

from tests.base import OsfTestCase


class TestMetaData(OsfTestCase):

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

    def test_process(self):
        processed = process_payload({'foo': 'bar&baz'})
        assert_equal(processed['foo'], 'bar%26baz')

    def test_process_list(self):
        processed = process_payload({'foo': ['bar', 'baz&bob']})
        assert_equal(processed['foo'][1], 'baz%26bob')

    def test_process_whitespace(self):
        processed = process_payload({'foo': 'bar baz'})
        assert_equal(processed['foo'], 'bar baz')


if __name__ == '__main__':
    unittest.main()
