# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

from framework.forms.utils import process_payload
from modularodm.exceptions import KeyExistsException

from website.project.model import MetaSchema
from website.project.model import ensure_schemas
from website.project.metadata.schemas import OSF_META_SCHEMAS

from tests.base import DbIsolationMixin, OsfTestCase


class TestMetaData(DbIsolationMixin, OsfTestCase):

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

    def test_metaschema_uniqueness_is_enforced_in_the_database(self):
        # Using MongoDB's uniqueness instead of modular-odm's allows us to
        # kludge a race-less upsert in ensure_schema.
        MetaSchema(name='foo', schema_version=1).save()
        assert_raises(KeyExistsException, MetaSchema(name='foo', schema_version=1).save)
        # modular-odm's uniqueness constraint would raise ValidationValueError instead.

    def test_metaschema_is_fine_with_same_name_but_different_version(self):
        MetaSchema(name='foo', schema_version=1).save()
        MetaSchema(name='foo', schema_version=2).save()
        assert_equal(MetaSchema.find(name='foo').count(), 2)

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
