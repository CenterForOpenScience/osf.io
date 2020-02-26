# -*- coding: utf-8 -*-
import os
import mock
import lxml
import pytest
import responses
from nose.tools import *  # noqa

from datacite import schema40

from framework.auth import Auth

from website import settings
from website.identifiers.clients import DataCiteClient
from website.identifiers.utils import request_identifiers

from tests.base import OsfTestCase
from tests.test_addons import assert_urls_equal
from osf_tests.factories import AuthUserFactory, RegistrationFactory, ProjectFactory


HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, 'fixtures')

@pytest.fixture(autouse=True)
def override_doi_settings():
    settings.DOI_FORMAT = '{prefix}/FK2osf.io/{guid}'

@pytest.fixture()
def datacite_client(registration):
    class MockDataciteClient(object):
        def __init__(self, *arg, **kwargs):
            pass

        url = 'https://mds.fakedatacite.org'
        metadata_get = mock.Mock(return_value=datacite_metadata_response())
        metadata_post = mock.Mock(return_value='OK (10.70102/FK2osf.io/{})'.format(registration._id))
        doi_post = mock.Mock(return_value='OK (10.70102/FK2osf.io/{})'.format(registration._id))
        metadata_delete = mock.Mock(return_value='OK heeeeeeey')

    return DataCiteClient(
        base_url = 'https://mds.fake.datacite.org',
        prefix=settings.DATACITE_PREFIX,
        client=MockDataciteClient()
    )

@pytest.fixture()
def registration():
    return RegistrationFactory(is_public=True)

@pytest.fixture()
def datacite_metadata_response():
    with open(os.path.join(FIXTURES, 'datacite_post_metadata_response.xml'), 'r') as fp:
        return fp.read()


@pytest.mark.django_db
class TestDataCiteClient:

    def test_datacite_create_identifiers(self, registration, datacite_client):
        identifiers = datacite_client.create_identifier(node=registration, category='doi')
        datacite_node_metadata = datacite_client.build_metadata(node=registration)

        assert identifiers['doi'] == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)
        datacite_client._client.metadata_post.assert_called_with(datacite_node_metadata)

    def test_datacite_update_doi_public_registration(self, registration, datacite_client):
        identifiers = datacite_client.update_identifier(registration, category='doi')
        datacite_node_metadata = datacite_client.build_metadata(registration)

        assert identifiers['doi'] == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)
        datacite_client._client.metadata_post.assert_called_with(datacite_node_metadata)

    def test_datacite_update_doi_status_unavailable(self, datacite_client):
        node = ProjectFactory(is_public=False)
        datacite_client.update_identifier(node, category='doi')

        assert datacite_client._client.metadata_delete.called

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

        resource_type = root.find('{%s}resourceType' % schema40.ns[None])
        assert resource_type.text == 'Project'
        assert resource_type.attrib['resourceTypeGeneral'] == 'Text'

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
                body='OK (10.70102/FK2osf.io/cq695)',
                status=201,
            )
        )
        responses.add(
            responses.Response(
                responses.POST,
                self.client.base_url + '/doi',
                body='OK (10.70102/FK2osf.io/cq695)',
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

    def test_qatest_doesnt_make_dois(self):
        self.node.add_tag('qatest', auth=Auth(self.user))
        assert not request_identifiers(self.node)
