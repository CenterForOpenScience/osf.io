# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

from django.db import IntegrityError

from osf_tests.factories import (
    IdentifierFactory,
    RegistrationFactory,
)

from tests.base import OsfTestCase

from osf.models import Identifier


class TestIdentifierModel(OsfTestCase):

    def test_fields(self):
        node = RegistrationFactory()
        identifier = Identifier(referent=node, category='catid', value='cat:7')
        assert_equal(identifier.referent, node)
        assert_equal(identifier.category, 'catid')
        assert_equal(identifier.value, 'cat:7')

    def test_unique_constraint(self):
        node = RegistrationFactory()
        IdentifierFactory(referent=node)
        with assert_raises(IntegrityError):
            IdentifierFactory(referent=node)

    def test_mixin_get(self):
        identifier = IdentifierFactory()
        node = identifier.referent
        assert_equal(node.get_identifier(identifier.category), identifier)

    def test_mixin_get_value(self):
        identifier = IdentifierFactory()
        node = identifier.referent
        assert_equal(node.get_identifier_value(identifier.category), identifier.value)

    def test_mixin_set_create(self):
        node = RegistrationFactory()
        assert_is_none(node.get_identifier('dogid'))
        node.set_identifier_value('dogid', 'dog:1')
        assert_equal(node.get_identifier_value('dogid'), 'dog:1')

    def test_mixin_set_update(self):
        identifier = IdentifierFactory(category='dogid', value='dog:1')
        node = identifier.referent
        assert_equal(node.get_identifier_value('dogid'), 'dog:1')
        node.set_identifier_value('dogid', 'dog:2')
        assert_equal(node.get_identifier_value('dogid'), 'dog:2')

    def test_node_csl(self):
        node = RegistrationFactory()
        node.set_identifier_value('doi', 'FK424601')
        assert_equal(node.csl['DOI'], 'FK424601')

    def test_get_identifier_for_doi_returns_legacy_doi(self):
        identifier = IdentifierFactory(category='legacy_doi', value='hello')
        preprint = identifier.referent
        assert preprint.get_identifier_value('doi') == 'hello'
