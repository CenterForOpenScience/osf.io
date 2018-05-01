# -*- coding: utf-8 -*-
import mock
import responses
from nose.tools import *  # noqa

from django.db import IntegrityError

from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory
from osf_tests.factories import IdentifierFactory
from osf_tests.factories import RegistrationFactory
from osf_tests.factories import PreprintFactory, SubjectFactory, PreprintProviderFactory
from tests.test_addons import assert_urls_equal

import furl
import lxml.etree

from website import settings
from website.identifiers.utils import to_anvl
from website.identifiers import metadata
from website.identifiers.client import CrossRefClient
from website.identifiers.utils import build_doi_metadata
from osf.models import Identifier, Subject, NodeLicense


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
        metadata_xml = metadata.datacite_metadata_for_node(self.node, doi=self.identifier.value)
        # includes visible contrib name
        assert_in(u'{}, {}'.format(
            self.visible_contrib.family_name, self.visible_contrib.given_name),
            metadata_xml)
        # doesn't include invisible contrib name
        assert_not_in(self.invisible_contrib.family_name, metadata_xml)

        assert_in(self.identifier.value, metadata_xml)

    def test_metadata_for_node_has_correct_structure(self):
        metadata_xml = metadata.datacite_metadata_for_node(self.node, doi=self.identifier.value)
        root = lxml.etree.fromstring(metadata_xml)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd'
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

    def test_metadata_for_preprint_has_correct_structure(self):
        provider = PreprintProviderFactory()
        license = NodeLicense.objects.get(name="CC-By Attribution 4.0 International")
        license_details = {
            'id': license.license_id,
            'year': '2017',
            'copyrightHolders': ['Jeff Hardy', 'Matt Hardy']
        }
        preprint = PreprintFactory(provider=provider, project=self.node, is_published=True, license_details=license_details)
        metadata_xml = metadata.datacite_metadata_for_preprint(preprint, doi=preprint.get_identifier('doi').value, pretty_print=True)

        root = lxml.etree.fromstring(metadata_xml)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd'
        assert root.attrib[xsi_location] == expected_location

        identifier = root.find('{%s}identifier' % metadata.NAMESPACE)
        assert identifier.attrib['identifierType'] == 'DOI'
        assert identifier.text == preprint.get_identifier('doi').value

        creators = root.find('{%s}creators' % metadata.NAMESPACE)
        assert len(creators.getchildren()) == len(self.node.visible_contributors)

        subjects = root.find('{%s}subjects' % metadata.NAMESPACE)
        assert subjects.getchildren()

        publisher = root.find('{%s}publisher' % metadata.NAMESPACE)
        assert publisher.text == provider.name

        pub_year = root.find('{%s}publicationYear' % metadata.NAMESPACE)
        assert pub_year.text == str(preprint.date_published.year)

        dates = root.find('{%s}dates' % metadata.NAMESPACE).getchildren()[0]
        assert dates.text == preprint.modified.isoformat()
        assert dates.attrib['dateType'] == 'Updated'

        alternate_identifier = root.find('{%s}alternateIdentifiers' % metadata.NAMESPACE).getchildren()[0]
        assert alternate_identifier.text == settings.DOMAIN + preprint._id
        assert alternate_identifier.attrib['alternateIdentifierType'] == 'URL'

        descriptions = root.find('{%s}descriptions' % metadata.NAMESPACE).getchildren()[0]
        assert descriptions.text == preprint.node.description

        rights = root.find('{%s}rightsList' % metadata.NAMESPACE).getchildren()[0]
        assert rights.text == preprint.license.name

    def test_format_creators_for_preprint(self):
        preprint = PreprintFactory(project=self.node, is_published=True)

        verified_user = AuthUserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}})
        linked_user = AuthUserFactory(external_identity={'ORCID': {'1234-nope-1234-nope': 'LINK'}})
        self.node.add_contributor(verified_user, visible=True)
        self.node.add_contributor(linked_user, visible=True)
        self.node.save()

        formatted_creators = metadata.format_creators(preprint)

        contributors_with_orcids = 0
        guid_identifiers = []
        for creator_xml in formatted_creators:
            assert creator_xml.find('creatorName').text != u'{}, {}'.format(self.invisible_contrib.family_name, self.invisible_contrib.given_name)

            name_identifiers = creator_xml.findall('nameIdentifier')

            for name_identifier in name_identifiers:
                if name_identifier.attrib['nameIdentifierScheme'] == 'ORCID':
                    assert name_identifier.attrib['schemeURI'] == 'http://orcid.org/'
                    contributors_with_orcids += 1
                else:
                    guid_identifiers.append(name_identifier.text)
                    assert name_identifier.attrib['nameIdentifierScheme'] == 'OSF'
                    assert name_identifier.attrib['schemeURI'] == settings.DOMAIN

        assert contributors_with_orcids >= 1
        assert len(formatted_creators) == len(self.node.visible_contributors)
        assert sorted(guid_identifiers) == sorted([contrib.absolute_url for contrib in self.node.visible_contributors])

    def test_format_subjects_for_preprint(self):
        subject = SubjectFactory()
        subject_1 = SubjectFactory(parent=subject)
        subject_2 = SubjectFactory(parent=subject)

        subjects = [[subject._id, subject_1._id], [subject._id, subject_2._id]]
        preprint = PreprintFactory(subjects=subjects, project=self.node, is_published=True)

        formatted_subjects = metadata.format_subjects(preprint)
        assert len(formatted_subjects) == Subject.objects.all().count()

    def test_crossref_metadata_has_correct_structure(self):
        provider = PreprintProviderFactory()
        license = NodeLicense.objects.get(name="CC-By Attribution 4.0 International")
        license_details = {
            'id': license.license_id,
            'year': '2017',
            'copyrightHolders': ['Jeff Hardy', 'Matt Hardy']
        }
        preprint = PreprintFactory(provider=provider, project=self.node, is_published=True, license_details=license_details)
        doi = settings.DOI_FORMAT.format(namespace=preprint.provider.doi_prefix, guid=preprint._id)
        crossref_xml = metadata.crossref_metadata_for_preprint(preprint, doi, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)
        contributors = root.find(".//{%s}contributors" % metadata.CROSSREF_NAMESPACE)

        assert len(contributors.getchildren()) == len(preprint.node.visible_contributors)
        assert root.find('.//{%s}license_ref' % metadata.CROSSREF_ACCESS_INDICATORS).text == license.url
        assert root.find('.//{%s}abstract/' % metadata.JATS_NAMESPACE).text == preprint.node.description

        # TODO - finish this test!


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


class TestIdentifierViews(OsfTestCase):

    def setUp(self):
        super(TestIdentifierViews, self).setUp()

        self.user = AuthUserFactory()
        self.node = RegistrationFactory(creator=self.user, is_public=True)

        self.mock_crossref_response = """
        \n\n\n\n<html>\n<head><title>SUCCESS</title>\n</head>\n<body>\n<h2>SUCCESS</h2>\n<p>
        Your batch submission was successfully received.</p>\n</body>\n</html>\n
        """

    @responses.activate
    @mock.patch('website.settings.EZID_USERNAME', 'testfortravisnotreal')
    @mock.patch('website.settings.EZID_PASSWORD', 'testfortravisnotreal')
    def test_create_identifiers_not_exists(self):
        identifier = self.node._id
        url = furl.furl('https://ezid.cdlib.org/id')
        doi = settings.DOI_FORMAT.format(namespace=settings.EZID_DOI_NAMESPACE, guid=identifier)
        url.path.segments.append(doi)
        responses.add(
            responses.Response(
                responses.PUT,
                url.url,
                body=to_anvl({
                    'success': '{doi}osf.io/{ident} | {ark}osf.io/{ident}'.format(
                        doi=settings.EZID_DOI_NAMESPACE,
                        ark=settings.EZID_ARK_NAMESPACE,
                        ident=identifier,
                    ),
                }),
                status=201,
            )
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
        assert_equal(res.status_code, 201)

    @responses.activate
    @mock.patch('website.settings.EZID_USERNAME', 'testfortravisnotreal')
    @mock.patch('website.settings.EZID_PASSWORD', 'testfortravisnotreal')
    def test_create_identifiers_exists(self):
        identifier = self.node._id
        doi = settings.DOI_FORMAT.format(namespace=settings.EZID_DOI_NAMESPACE, guid=identifier)
        url = furl.furl('https://ezid.cdlib.org/id')
        url.path.segments.append(doi)
        responses.add(
            responses.Response(
                responses.PUT,
                url.url,
                body='identifier already exists',
                status=400,
            )
        )

        responses.add(
            responses.Response(
                responses.GET,
                url.url,
                body=to_anvl({
                    'success': doi,
                }),
                status=200,
            )
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

    @responses.activate
    @mock.patch('website.settings.CROSSREF_USERNAME', 'thisisatest')
    @mock.patch('website.settings.CROSSREF_PASSWORD', 'thisisatest')
    @mock.patch('website.identifiers.client.CrossRefClient.BASE_URL', 'https://test.test.osf.io')
    def test_create_identifiers_crossref(self):

        responses.add(
            responses.Response(
                responses.POST,
                'https://test.test.osf.io',
                body=self.mock_crossref_response,
                content_type='text/html;charset=ISO-8859-1',
                status=200
            )
        )

        preprint = PreprintFactory(doi=None)
        doi, preprint_metadata = build_doi_metadata(preprint)
        client = CrossRefClient(settings.CROSSREF_USERNAME, settings.CROSSREF_PASSWORD)
        res = client.create_identifier(identifier=doi, metadata=preprint_metadata)

        assert res.status_code == 200
        assert 'SUCCESS' in res.content
