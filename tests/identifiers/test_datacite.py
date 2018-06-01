# -*- coding: utf-8 -*-
import os
import mock
import lxml
import pytest
import responses
from nose.tools import *  # noqa

from datacite import schema40

from website import settings
from website.app import init_addons
from website.identifiers.clients import DataCiteClient
from website.identifiers import metadata

from tests.base import OsfTestCase
from tests.identifiers.conftest import datacite_metadata_response
from tests.test_addons import assert_urls_equal
from osf_tests.factories import AuthUserFactory, RegistrationFactory

class MockDataciteClient(object):

    def __init__(self, *arg, **kwargs):
        pass

    url = 'https://mds.fake.datacite.org'
    metadata_get = mock.Mock(return_value=datacite_metadata_response())
    metadata_post = mock.Mock(return_value='OK (10.5072/FK2osf.io/yvzp4)')

@pytest.fixture()
def datacite_client():
    return DataCiteClient(
        base_url = 'https://mds.fake.datacite.org',
        prefix=settings.DATACITE_PREFIX
    )

@pytest.fixture()
def registration():
    return RegistrationFactory()

@pytest.mark.django_db
class TestDataCiteClient:

    @responses.activate
    @mock.patch('website.identifiers.clients.datacite.DataCiteMDSClient', MockDataciteClient)
    def test_datacite_create_identifiers(self, datacite_client, datacite_node_metadata):
        responses.add(
            responses.Response(
                responses.POST,
                datacite_client.base_url + '/metadata',
                body='OK',
                status=200
            )
        )
        identifiers = datacite_client.create_identifier(datacite_node_metadata)

        assert identifiers['doi'] == '10.5072/FK2osf.io/yvzp4'
        MockDataciteClient.metadata_post.assert_called_with(datacite_node_metadata)

    @responses.activate
    @mock.patch('website.identifiers.clients.datacite.DataCiteMDSClient', MockDataciteClient)
    def test_datacite_change_status_identifier(self, datacite_client, datacite_node_metadata):
        responses.add(
            responses.Response(
                responses.POST,
                datacite_client.base_url + '/metadata',
                body='OK',
                status=200
            )
        )

        identifiers = datacite_client.change_status_identifier(status=None, metadata=datacite_node_metadata)

        assert identifiers['doi'] == '10.5072/FK2osf.io/yvzp4'
        MockDataciteClient.metadata_post.assert_called_with(datacite_node_metadata)

    def test_datacite_build_doi(self, registration, datacite_client):
        assert datacite_client.build_doi(registration) == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

    def test_datacite_build_metadata(self, registration, datacite_client):
        metadata_xml = datacite_client.build_metadata(registration).encode('utf-8')
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd'
        assert root.attrib[xsi_location] == expected_location

        identifier = root.find('{%s}identifier' % schema40.ns[None])
        assert identifier.attrib['identifierType'] == 'DOI'
        assert identifier.text == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

        creators = root.find('{%s}creators' % schema40.ns[None])
        assert len(creators.getchildren()) == len(registration.visible_contributors)

        publisher = root.find('{%s}publisher' % schema40.ns[None])
        assert publisher.text == 'Open Science Framework'

        pub_year = root.find('{%s}publicationYear' % schema40.ns[None])
        assert pub_year.text == str(registration.registered_date.year)

    def test_metadata_for_node_only_includes_visible_contribs(self, datacite_client):
        visible_contrib = AuthUserFactory()
        visible_contrib2 = AuthUserFactory()
        visible_contrib2.given_name = u'ヽ༼ ಠ益ಠ ༽ﾉ'
        visible_contrib2.family_name = u'ლ(´◉❥◉｀ლ)'
        visible_contrib2.save()
        invisible_contrib = AuthUserFactory()
        invisible_contrib.given_name = 'Shady'
        invisible_contrib.family_name = 'McCoy'
        invisible_contrib.save()
        registration = RegistrationFactory(is_public=True)

        registration.add_contributor(visible_contrib, visible=True)
        registration.add_contributor(invisible_contrib, visible=False)
        registration.add_contributor(visible_contrib2, visible=True)
        registration.save()

        metadata_xml = datacite_client.build_metadata(registration)
        # includes visible contrib name
        assert u'<givenName>{}</givenName>'.format(visible_contrib.given_name) in metadata_xml
        assert u'<familyName>{}</familyName>'.format(visible_contrib.family_name) in metadata_xml

        # doesn't include invisible contrib name
        assert u'<givenName>{}</givenName>'.format(invisible_contrib.given_name) not in metadata_xml
        assert u'<familyName>{}</familyName>'.format(invisible_contrib.family_name) not in metadata_xml


@pytest.mark.django_db
class TestDataCiteViews(OsfTestCase):
    """ This tests the v1 views for Project/Registration DOI creation."""

    def setUp(self):
        super(TestDataCiteViews, self).setUp()
        self.user = AuthUserFactory()
        self.node = RegistrationFactory(creator=self.user, is_public=True)
        self.client = DataCiteClient(base_url = 'https://mds.fake.datacite.org', prefix=settings.DATACITE_PREFIX)

    @responses.activate
    def test_datacite_create_identifiers_not_exists(self):
        responses.add(
            responses.Response(
                responses.POST,
                self.client.base_url + '/metadata',
                body='OK (10.5072/FK2osf.io/cq695)',
                status=201,
            )
        )
        with mock.patch('osf.models.Registration.get_doi_client') as mock_get_doi:
            mock_get_doi.return_value = self.client
            res = self.app.post(
                self.node.api_url_for('node_identifiers_post'),
                auth=self.user.auth,
            )
        self.node.reload()
        assert res.json['doi'] == self.node.get_identifier_value('doi')
        assert res.status_code == 201

    @responses.activate
    def test_datacite_get_by_identifier(self):
        self.node.set_identifier_value('doi', 'FK424601')
        self.node.set_identifier_value('ark', 'fk224601')

        with mock.patch('osf.models.Registration.get_doi_client') as mock_get_doi:
            mock_get_doi.return_value = self.client

            res_doi = self.app.get(
                self.node.web_url_for(
                    'get_referent_by_identifier',
                    category='doi',
                    value=self.node.get_identifier_value('doi'),
                ),
            )

        assert res_doi.status_code == 302
        assert_urls_equal(res_doi.headers['Location'], self.node.absolute_url)

    @responses.activate
    def test_datacite_get_by_identifier_not_found(self):
        self.node.set_identifier_value('doi', 'FK424601')
        with mock.patch('osf.models.Registration.get_doi_client') as mock_get_doi:
            mock_get_doi.return_value = self.client
            res = self.app.get(
                self.node.web_url_for(
                    'get_referent_by_identifier',
                    category='doi',
                    value='fakedoi',
                ),
                expect_errors=True,
            )
        assert res.status_code == 404
