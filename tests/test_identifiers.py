# -*- coding: utf-8 -*-

import httpretty
from factory import SubFactory
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from tests.factories import ModularOdmFactory
from tests.factories import RegistrationFactory

import furl
from modularodm.storage.base import KeyExistsException

from website import settings
from website.identifiers.utils import to_anvl
from website.identifiers.model import Identifier


class IdentifierFactory(ModularOdmFactory):
    FACTORY_FOR = Identifier

    referent = SubFactory(RegistrationFactory)
    category = 'carpid'
    value = 'carp:/24601'


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


class TestIdentifierViews(OsfTestCase):

    def setUp(self):
        super(TestIdentifierViews, self).setUp()
        self.user = AuthUserFactory()
        self.node = RegistrationFactory(creator=self.user, is_public=True)

    def test_get_identifiers(self):
        self.node.set_identifier_value('doi', 'FK424601')
        self.node.set_identifier_value('ark', 'fk224601')
        res = self.app.get(self.node.api_url_for('node_identifiers_get'))
        assert_equal(res.json['doi'], 'FK424601')
        assert_equal(res.json['ark'], 'fk224601')

    def test_create_identifiers_not_exists(self):
        identifier = self.node._id
        url = furl.furl('https://ezid.cdlib.org/id')
        url.path.segments.append('{0}{1}'.format(settings.DOI_NAMESPACE, identifier))
        httpretty.register_uri(
            httpretty.PUT,
            url.url,
            body=to_anvl({
                'success': '{doi}{ident} | {ark}{ident}'.format(
                    doi=settings.DOI_NAMESPACE,
                    ark=settings.ARK_NAMESPACE,
                    ident=identifier,
                ),
            }),
            status=201,
            priority=1,
        )
        res = self.app.post(
            self.node.api_url_for('node_identifiers_post'),
            auth=self.user.auth,
        )
        assert_equal(
            res.json['doi'],
            '{0}{1}'.format(settings.DOI_NAMESPACE.strip('doi:'), identifier)
        )
        assert_equal(
            res.json['ark'],
            '{0}{1}'.format(settings.ARK_NAMESPACE.strip('ark:'), identifier),
        )
        assert_equal(res.status_code, 201)

    def test_create_identifiers_exists(self):
        identifier = self.node._id
        url = furl.furl('https://ezid.cdlib.org/id')
        url.path.segments.append('{0}{1}'.format(settings.DOI_NAMESPACE, identifier))
        httpretty.register_uri(
            httpretty.PUT,
            url.url,
            body='identifier already exists',
            status=400,
        )
        httpretty.register_uri(
            httpretty.GET,
            url.url,
            body=to_anvl({
                'success': '{0}{1}'.format(settings.DOI_NAMESPACE, identifier),
            }),
            status=200,
        )
        res = self.app.post(
            self.node.api_url_for('node_identifiers_post'),
            auth=self.user.auth,
        )
        assert_equal(
            res.json['doi'],
            '{0}{1}'.format(settings.DOI_NAMESPACE.strip('doi:'), identifier)
        )
        assert_equal(
            res.json['ark'],
            '{0}{1}'.format(settings.ARK_NAMESPACE.strip('ark:'), identifier),
        )
        assert_equal(res.status_code, 201)
