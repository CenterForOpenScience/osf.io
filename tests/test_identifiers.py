# -*- coding: utf-8 -*-

import httpretty
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from tests.factories import IdentifierFactory
from tests.factories import RegistrationFactory
from tests.test_addons import assert_urls_equal

import furl
import lxml.etree
from modularodm.storage.base import KeyExistsException

from website import settings
from website.identifiers.utils import to_anvl
from website.identifiers.model import Identifier
from website.identifiers.metadata import datacite_metadata_for_node
from website.identifiers import metadata


class TestMetadataGeneration(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.visible_contrib = AuthUserFactory()
        visible_contrib2 = AuthUserFactory(given_name=u'ヽ༼ ಠ益ಠ ༽ﾉ', family_name=u'ლ(´◉❥◉｀ლ)')
        self.invisible_contrib = AuthUserFactory()
        self.node = RegistrationFactory(is_public=True)
        self.identifier = Identifier(referent=self.node, category='catid', value='cat:7')
        self.node.add_contributor(self.visible_contrib, visible=True)
        self.node.add_contributor(self.invisible_contrib, visible=False)
        self.node.add_contributor(visible_contrib2, visible=True)
        self.node.save()

    def test_metadata_for_node_only_includes_visible_contribs(self):
        metadata_xml = datacite_metadata_for_node(self.node, doi=self.identifier.value)
        # includes visible contrib name
        assert_in(u'{}, {}'.format(
            self.visible_contrib.family_name, self.visible_contrib.given_name),
            metadata_xml)
        # doesn't include invisible contrib name
        assert_not_in(self.invisible_contrib.family_name, metadata_xml)

        assert_in(self.identifier.value, metadata_xml)

    def test_metadata_for_node_has_correct_structure(self):
        metadata_xml = datacite_metadata_for_node(self.node, doi=self.identifier.value)
        root = lxml.etree.fromstring(metadata_xml)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-3 http://schema.datacite.org/meta/kernel-3/metadata.xsd'
        assert_equal(root.attrib[xsi_location], expected_location)

        identifier = root.find('{%s}identifier' % metadata.NAMESPACE)
        assert_equal(identifier.attrib['identifierType'], 'DOI')
        assert_equal(identifier.text, self.identifier.value)

        creators = root.find('{%s}creators' % metadata.NAMESPACE)
        assert_equal(len(creators.getchildren()), len(self.node.visible_contributors))

        publisher = root.find('{%s}publisher' % metadata.NAMESPACE)
        assert_equal(publisher.text, 'Open Science Framework')

        pub_year = root.find('{%s}publicationYear' % metadata.NAMESPACE)
        assert_equal(pub_year.text, str(self.node.registered_date.year))


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

    @httpretty.activate
    def test_create_identifiers_not_exists(self):
        identifier = self.node._id
        url = furl.furl('https://ezid.cdlib.org/id')
        doi = settings.EZID_FORMAT.format(namespace=settings.DOI_NAMESPACE, guid=identifier)
        url.path.segments.append(doi)
        httpretty.register_uri(
            httpretty.PUT,
            url.url,
            body=to_anvl({
                'success': '{doi}osf.io/{ident} | {ark}osf.io/{ident}'.format(
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
        self.node.reload()
        assert_equal(
            res.json['doi'],
            self.node.get_identifier_value('doi')
        )
        assert_equal(
            res.json['ark'],
            self.node.get_identifier_value('ark')
        )
        assert_equal(res.status_code, 201)


    @httpretty.activate
    def test_create_identifiers_exists(self):
        identifier = self.node._id
        doi = settings.EZID_FORMAT.format(namespace=settings.DOI_NAMESPACE, guid=identifier)
        url = furl.furl('https://ezid.cdlib.org/id')
        url.path.segments.append(doi)
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
                'success': doi,
            }),
            status=200,
        )
        res = self.app.post(
            self.node.api_url_for('node_identifiers_post'),
            auth=self.user.auth,
        )
        self.node.reload()
        assert_equal(
            res.json['doi'],
            self.node.get_identifier_value('doi')
        )
        assert_equal(
            res.json['ark'],
            self.node.get_identifier_value('ark')
        )
        assert_equal(res.status_code, 201)

    def test_get_by_identifier(self):
        self.node.set_identifier_value('doi', 'FK424601')
        self.node.set_identifier_value('ark', 'fk224601')
        res_doi = self.app.get(
            self.node.web_url_for(
                'get_referent_by_identifier',
                category='doi',
                value=self.node.get_identifier_value('doi'),
            ),
        )
        assert_equal(res_doi.status_code, 302)
        assert_urls_equal(res_doi.headers['Location'], self.node.absolute_url)
        res_ark = self.app.get(
            self.node.web_url_for(
                'get_referent_by_identifier',
                category='ark',
                value=self.node.get_identifier_value('ark'),
            ),
        )
        assert_equal(res_ark.status_code, 302)
        assert_urls_equal(res_ark.headers['Location'], self.node.absolute_url)

    def test_get_by_identifier_not_found(self):
        self.node.set_identifier_value('doi', 'FK424601')
        res = self.app.get(
            self.node.web_url_for(
                'get_referent_by_identifier',
                category='doi',
                value='fakedoi',
            ),
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
