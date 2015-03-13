# -*- coding: utf-8 -*-

from nose.tools import *  # noqa
from factory import SubFactory

from tests.base import OsfTestCase
from tests.factories import NodeFactory
from tests.factories import ModularOdmFactory

from modularodm.storage.base import KeyExistsException

from website.identifiers.model import Identifier


class IdentifierFactory(ModularOdmFactory):
    FACTORY_FOR = Identifier

    referent = SubFactory(NodeFactory)
    category = 'carpid'
    value = 'carp:/24601'


class TestIdentifierModel(OsfTestCase):

    def test_fields(self):
        node = NodeFactory()
        identifier = Identifier(referent=node, category='catid', value='cat:7')
        assert_equal(identifier.referent, node)
        assert_equal(identifier.category, 'catid')
        assert_equal(identifier.value, 'cat:7')

    def test_unique_constraint(self):
        node = NodeFactory()
        IdentifierFactory(referent=node)
        with assert_raises(KeyExistsException):
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
        node = NodeFactory()
        assert_is_none(node.get_identifier('dogid'))
        node.set_identifier_value('dogid', 'dog:1')
        assert_equal(node.get_identifier_value('dogid'), 'dog:1')

    def test_mixin_set_update(self):
        identifier = IdentifierFactory(category='dogid', value='dog:1')
        node = identifier.referent
        assert_equal(node.get_identifier_value('dogid'), 'dog:1')
        node.set_identifier_value('dogid', 'dog:2')
        assert_equal(node.get_identifier_value('dogid'), 'dog:2')
