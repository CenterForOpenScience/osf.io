import lxml
import pytest
import responses

from datacite import schema40
from django.utils import timezone

from framework.auth import Auth
from osf.models import GuidMetadataRecord, Outcome
from osf.utils.outcomes import ArtifactTypes
from osf_tests.factories import AuthUserFactory, IdentifierFactory, RegistrationFactory
from tests.base import OsfTestCase
from tests.test_addons import assert_urls_equal
from website import settings
from website.identifiers.clients import DataCiteClient
from website.identifiers.utils import request_identifiers


def _frozendict(dictionary: dict):
    return frozenset(dictionary.items())


def _assert_unordered_list_of_dicts_equal(actual_list_of_dicts, expected_list_of_dicts):
    actual = frozenset(map(_frozendict, actual_list_of_dicts))
    expected = frozenset(map(_frozendict, expected_list_of_dicts))
    assert actual == expected


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
class TestDataCiteClient:

    @pytest.fixture()
    def datacite_client(self, registration, mock_datacite):
        return registration.get_doi_client()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(is_public=True, creator=user)

    def test_datacite_create_identifiers(self, registration, datacite_client, mock_datacite):
        identifiers = datacite_client.create_identifier(node=registration, category='doi')
        assert identifiers['doi'] == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

        assert len(mock_datacite.calls) == 2
        datacite_metadata = mock_datacite.calls[0].request.body
        assert datacite_metadata == datacite_client.build_metadata(node=registration)
        doi_body = mock_datacite.calls[1].request.body
        assert doi_body == f'doi={identifiers["doi"]}\r\nurl=http://localhost:5000/{registration._id}/'.encode()

    def test_datacite_update_doi_public_registration(self, registration, datacite_client, mock_datacite):
        identifiers = datacite_client.update_identifier(registration, category='doi')
        assert identifiers['doi'] == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

        assert len(mock_datacite.calls) == 2
        datacite_metadata = mock_datacite.calls[0].request.body
        assert datacite_metadata == datacite_client.build_metadata(node=registration)
        doi_body = mock_datacite.calls[1].request.body
        assert doi_body == f'doi={identifiers["doi"]}\r\nurl=http://localhost:5000/{registration._id}/'.encode()

    def test_datacite_update_doi_status_unavailable(self, registration, datacite_client, mock_datacite):
        registration.is_public = False
        registration.save()
        identifiers = datacite_client.update_identifier(registration, category='doi')

        assert len(mock_datacite.calls) == 1
        assert mock_datacite.calls[0].request.body is None
        assert mock_datacite.calls[0].request.method == 'DELETE'
        assert mock_datacite.calls[0].request.url == f'{settings.DATACITE_URL}/metadata/{identifiers["doi"]}'

    def test_datacite_build_doi(self, registration, datacite_client):
        assert datacite_client.build_doi(registration) == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

    def test_datacite_build_metadata(self, registration, datacite_client):
        metadata_xml = datacite_client.build_metadata(registration)
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.5/metadata.xsd'
        assert root.attrib[xsi_location] == expected_location

        identifier = root.find('{%s}identifier' % schema40.ns[None])
        assert identifier.attrib['identifierType'] == 'DOI'
        assert identifier.text == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

        creators = root.find('{%s}creators' % schema40.ns[None])
        assert len(creators.getchildren()) == len(registration.visible_contributors)

        publisher = root.find('{%s}publisher' % schema40.ns[None])
        assert publisher.text == 'OSF Registries'

        pub_year = root.find('{%s}publicationYear' % schema40.ns[None])
        assert pub_year.text == str(registration.registered_date.year)

        resource_type = root.find('{%s}resourceType' % schema40.ns[None])
        assert resource_type.text == 'Pre-registration'
        assert resource_type.attrib['resourceTypeGeneral'] == 'StudyRegistration'

    def test_datacite_build_metadata_for_dataarchive_registration(self, registration, datacite_client):
        registration.provider._id = 'dataarchive'
        registration.provider.save()
        metadata_xml = datacite_client.build_metadata(registration)
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        xsi_location = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'
        expected_location = 'http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.5/metadata.xsd'
        assert root.attrib[xsi_location] == expected_location

        identifier = root.find('{%s}identifier' % schema40.ns[None])
        assert identifier.attrib['identifierType'] == 'DOI'
        assert identifier.text == settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=registration._id)

        creators = root.find('{%s}creators' % schema40.ns[None])
        assert len(creators.getchildren()) == len(registration.visible_contributors)

        publisher = root.find('{%s}publisher' % schema40.ns[None])
        assert publisher.text == 'OSF Registries'

        pub_year = root.find('{%s}publicationYear' % schema40.ns[None])
        assert pub_year.text == str(registration.registered_date.year)

        resource_type = root.find('{%s}resourceType' % schema40.ns[None])
        assert resource_type.text == 'Pre-registration'
        assert resource_type.attrib['resourceTypeGeneral'] == 'Dataset'

    def test_datacite_creators_follow_osf_contributor_order(self, datacite_client):
        registration = RegistrationFactory(is_public=True)
        first = registration.creator
        second = AuthUserFactory()
        third = AuthUserFactory()
        registration.add_contributor(third, visible=True)
        registration.add_contributor(second, visible=True)
        registration.save()

        visible_contributors = list(registration.visible_contributors)
        correct_order = [u.fullname for u in visible_contributors]
        assert correct_order == [
            first.fullname,
            third.fullname,
            second.fullname,
        ]

        metadata_xml = datacite_client.build_metadata(registration)
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        creators_el = root.find('{%s}creators' % schema40.ns[None])
        creator_elems = creators_el.findall('{%s}creator' % schema40.ns[None])
        xml_creator_names = [
            c.find('{%s}creatorName' % schema40.ns[None]).text
            for c in creator_elems
        ]
        assert xml_creator_names == correct_order

        auth = Auth(first)
        registration.move_contributor(first, auth=auth, index=2, save=True)
        registration.refresh_from_db()

        visible_contributors = list(registration.visible_contributors)
        new_correct_order = [u.fullname for u in visible_contributors]
        assert new_correct_order == [
            third.fullname,
            second.fullname,
            first.fullname,
        ]

        metadata_xml = datacite_client.build_metadata(registration)
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        creators_el = root.find('{%s}creators' % schema40.ns[None])
        creator_elems = creators_el.findall('{%s}creator' % schema40.ns[None])
        xml_creator_names = [
            c.find('{%s}creatorName' % schema40.ns[None]).text
            for c in creator_elems
        ]

        assert xml_creator_names == new_correct_order

    def test_datacite_format_contributors(self, datacite_client):
        visible_contrib = AuthUserFactory()
        visible_contrib2 = AuthUserFactory()
        visible_contrib2.given_name = 'ヽ༼ ಠ益ಠ ༽ﾉ'
        visible_contrib2.family_name = 'ლ(´◉❥◉｀ლ)'
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

        metadata_xml = datacite_client.build_metadata(registration).decode()
        # includes visible contrib name as creator
        assert f'<contributorName nameType="Personal">{visible_contrib.fullname}</contributorName>' not in metadata_xml
        assert f'<creatorName nameType="Personal">{visible_contrib.fullname}</creatorName>' in metadata_xml
        # does not include invisible contrib name
        assert f'<contributorName nameType="Personal">{invisible_contrib.fullname}</contributorName>' not in metadata_xml
        assert f'<creatorName nameType="Personal">{invisible_contrib.fullname}</creatorName>' not in metadata_xml

    def test_datacite_format_related_resources(self, datacite_client):
        registration = RegistrationFactory(is_public=True, has_doi=True, article_doi='10.pub/lication')
        outcome = Outcome.objects.for_registration(registration, create=True)
        data_artifact = outcome.artifact_metadata.create(
            identifier=IdentifierFactory(category='doi'), artifact_type=ArtifactTypes.DATA, finalized=True
        )
        materials_artifact = outcome.artifact_metadata.create(
            identifier=IdentifierFactory(category='doi'), artifact_type=ArtifactTypes.MATERIALS, finalized=True
        )

        metadata_dict = datacite_client.build_metadata(registration, as_xml=False)

        # Artifact entries first, ordered by type, followed by article doi
        expected_relationships = [
            {
                'relatedIdentifier': data_artifact.identifier.value,
                'relatedIdentifierType': 'DOI',
                'relationType': 'References',
            },
            {
                'relatedIdentifier': materials_artifact.identifier.value,
                'relatedIdentifierType': 'DOI',
                'relationType': 'References',
            },
            {
                'relatedIdentifier': '10.pub/lication',
                'relatedIdentifierType': 'DOI',
                'relationType': 'References',
            },
            {
                'relatedIdentifier': registration.registered_from.absolute_url.rstrip('/'),
                'relatedIdentifierType': 'URL',
                'relationType': 'IsVersionOf',
            },

        ]
        _assert_unordered_list_of_dicts_equal(metadata_dict['relatedIdentifiers'], expected_relationships)

    def test_datacite_format_related_resources__ignores_duplicate_pids(self, datacite_client):
        registration = RegistrationFactory(is_public=True, has_doi=True)
        outcome = Outcome.objects.for_registration(registration, create=True)
        identifier = IdentifierFactory(category='doi')
        outcome.artifact_metadata.create(
            identifier=identifier, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        outcome.artifact_metadata.create(
            identifier=identifier, artifact_type=ArtifactTypes.MATERIALS, finalized=True
        )

        metadata_dict = datacite_client.build_metadata(registration, as_xml=False)

        expected_relationships = [
            {
                'relatedIdentifier': identifier.value,
                'relatedIdentifierType': 'DOI',
                'relationType': 'References',
            },
            {
                'relatedIdentifier': registration.registered_from.absolute_url.strip('/'),
                'relatedIdentifierType': 'URL',
                'relationType': 'IsVersionOf',
            },
        ]
        _assert_unordered_list_of_dicts_equal(metadata_dict['relatedIdentifiers'], expected_relationships)

    def test_datacite_format_related_resources__ignores_inactive_resources(self, datacite_client):
        registration = RegistrationFactory(is_public=True, has_doi=True)
        outcome = Outcome.objects.for_registration(registration, create=True)
        active_artifact = outcome.artifact_metadata.create(
            identifier=IdentifierFactory(category='doi'), artifact_type=ArtifactTypes.DATA, finalized=True
        )
        nonfinal_artifact = outcome.artifact_metadata.create(
            identifier=IdentifierFactory(category='doi'), artifact_type=ArtifactTypes.DATA, finalized=False
        )
        deleted_artifact = outcome.artifact_metadata.create(
            identifier=IdentifierFactory(category='doi'),
            artifact_type=ArtifactTypes.DATA,
            finalized=False,
            deleted=timezone.now()
        )

        metadata_dict = datacite_client.build_metadata(registration, as_xml=False)

        expected_relationships = [
            {
                'relatedIdentifier': active_artifact.identifier.value,
                'relatedIdentifierType': 'DOI',
                'relationType': 'References',
            },
            {
                'relatedIdentifier': registration.registered_from.absolute_url.strip('/'),
                'relatedIdentifierType': 'URL',
                'relationType': 'IsVersionOf',
            },
        ]
        _assert_unordered_list_of_dicts_equal(metadata_dict['relatedIdentifiers'], expected_relationships)

    def _set_funding_info(self, registration, funding_info):
        metadata_record = GuidMetadataRecord.objects.for_guid(registration._id)
        metadata_record.funding_info = funding_info
        metadata_record.save()

    def test_datacite_funding_references_with_ror_identifier_xml(self, registration, datacite_client):
        self._set_funding_info(registration, [
            {
                'funder_name': 'National Science Foundation',
                'funder_identifier': 'https://ror.org/021nxhr62',
                'funder_identifier_type': 'ROR',
            },
        ])
        metadata_xml = datacite_client.build_metadata(registration)
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        ns = schema40.ns[None]

        funding_refs = root.find(f'{{{ns}}}fundingReferences')
        refs = funding_refs.findall(f'{{{ns}}}fundingReference')
        assert len(refs) == 1

        funder_name = refs[0].find(f'{{{ns}}}funderName')
        assert funder_name.text == 'National Science Foundation'

        funder_id = refs[0].find(f'{{{ns}}}funderIdentifier')
        assert funder_id.text == 'https://ror.org/021nxhr62'
        assert funder_id.attrib['funderIdentifierType'] == 'ROR'
        assert funder_id.attrib['schemeURI'] == 'https://ror.org/'

    def test_datacite_funding_references_with_ror_identifier_json(self, registration, datacite_client):
        self._set_funding_info(registration, [
            {
                'funder_name': 'National Science Foundation',
                'funder_identifier': 'https://ror.org/021nxhr62',
                'funder_identifier_type': 'ROR',
            },
        ])
        metadata_dict = datacite_client.build_metadata(registration, as_xml=False)

        funding_refs = metadata_dict['fundingReferences']
        assert len(funding_refs) == 1
        assert str(funding_refs[0]['funderName']) == 'National Science Foundation'
        assert funding_refs[0]['funderIdentifier']['funderIdentifier'] == 'https://ror.org/021nxhr62'
        assert funding_refs[0]['funderIdentifier']['funderIdentifierType'] == 'ROR'
        assert funding_refs[0]['funderIdentifier']['schemeURI'] == 'https://ror.org/'

    def test_datacite_funding_references_with_crossref_funder_id(self, registration, datacite_client):
        self._set_funding_info(registration, [
            {
                'funder_name': 'Mx. Moneypockets',
                'funder_identifier': 'https://doi.org/10.13039/100000001',
                'funder_identifier_type': 'Crossref Funder ID',
                'award_number': '10000000',
                'award_uri': 'https://moneypockets.example/millions',
                'award_title': 'because reasons',
            },
        ])
        metadata_xml = datacite_client.build_metadata(registration)
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        ns = schema40.ns[None]

        funding_refs = root.find(f'{{{ns}}}fundingReferences')
        refs = funding_refs.findall(f'{{{ns}}}fundingReference')
        assert len(refs) == 1

        funder_id = refs[0].find(f'{{{ns}}}funderIdentifier')
        assert funder_id.text == 'https://doi.org/10.13039/100000001'
        assert funder_id.attrib['funderIdentifierType'] == 'Crossref Funder ID'
        assert funder_id.attrib['schemeURI'] == 'https://www.crossref.org/services/funder-registry/'

        award_number = refs[0].find(f'{{{ns}}}awardNumber')
        assert award_number.text == '10000000'

    def test_datacite_funding_references_mixed_ror_and_crossref(self, registration, datacite_client):
        self._set_funding_info(registration, [
            {
                'funder_name': 'Mx. Moneypockets',
                'funder_identifier': 'https://doi.org/10.13039/100000001',
                'funder_identifier_type': 'Crossref Funder ID',
                'award_number': '10000000',
                'award_uri': 'https://moneypockets.example/millions',
                'award_title': 'because reasons',
            },
            {
                'funder_name': 'National Science Foundation',
                'funder_identifier': 'https://ror.org/021nxhr62',
                'funder_identifier_type': 'ROR',
            },
        ])
        metadata_dict = datacite_client.build_metadata(registration, as_xml=False)
        funding_refs = metadata_dict['fundingReferences']
        assert len(funding_refs) == 2

        # Build a lookup by funder name for order-independent assertions
        refs_by_name = {str(ref['funderName']): ref for ref in funding_refs}

        crossref_ref = refs_by_name['Mx. Moneypockets']
        assert crossref_ref['funderIdentifier']['funderIdentifier'] == 'https://doi.org/10.13039/100000001'
        assert crossref_ref['funderIdentifier']['funderIdentifierType'] == 'Crossref Funder ID'
        assert crossref_ref['funderIdentifier']['schemeURI'] == 'https://www.crossref.org/services/funder-registry/'
        assert crossref_ref['awardNumber']['awardNumber'] == '10000000'

        ror_ref = refs_by_name['National Science Foundation']
        assert ror_ref['funderIdentifier']['funderIdentifier'] == 'https://ror.org/021nxhr62'
        assert ror_ref['funderIdentifier']['funderIdentifierType'] == 'ROR'
        assert ror_ref['funderIdentifier']['schemeURI'] == 'https://ror.org/'

    def test_datacite_funding_references_ror_with_award_info(self, registration, datacite_client):
        self._set_funding_info(registration, [
            {
                'funder_name': 'National Institutes of Health',
                'funder_identifier': 'https://ror.org/01cwqze88',
                'funder_identifier_type': 'ROR',
                'award_number': 'R01-GM123456',
                'award_uri': 'https://reporter.nih.gov/project-details/123456',
                'award_title': 'Studying important things',
            },
        ])
        metadata_xml = datacite_client.build_metadata(registration)
        parser = lxml.etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        root = lxml.etree.fromstring(metadata_xml, parser=parser)
        ns = schema40.ns[None]

        funding_refs = root.find(f'{{{ns}}}fundingReferences')
        refs = funding_refs.findall(f'{{{ns}}}fundingReference')
        assert len(refs) == 1

        funder_id = refs[0].find(f'{{{ns}}}funderIdentifier')
        assert funder_id.text == 'https://ror.org/01cwqze88'
        assert funder_id.attrib['funderIdentifierType'] == 'ROR'
        assert funder_id.attrib['schemeURI'] == 'https://ror.org/'

        award_number = refs[0].find(f'{{{ns}}}awardNumber')
        assert award_number.text == 'R01-GM123456'

        award_title = refs[0].find(f'{{{ns}}}awardTitle')
        assert award_title.text == 'Studying important things'

    def test_datacite_funding_references_no_funding_info(self, registration, datacite_client):
        # With no funding info set, fundingReferences should be empty
        metadata_dict = datacite_client.build_metadata(registration, as_xml=False)
        assert metadata_dict.get('fundingReferences', []) == []


@pytest.mark.django_db
class TestDataCiteViews(OsfTestCase):
    """ This tests the v1 views for Project/Registration DOI creation."""

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = RegistrationFactory(creator=self.user, is_public=True)
        self.client = DataCiteClient(self.node)

    @responses.activate
    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_datacite_create_identifiers_not_exists(self):
        responses.add(
            responses.Response(
                responses.POST,
                settings.DATACITE_URL + '/metadata',
                body='OK (10.70102/FK2osf.io/cq695)',
                status=201,
            )
        )
        responses.add(
            responses.Response(
                responses.POST,
                settings.DATACITE_URL + '/doi',
                body='OK (10.70102/FK2osf.io/cq695)',
                status=201,
            )
        )
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
        res = self.app.get(
            self.node.web_url_for(
                'get_referent_by_identifier',
                category='doi',
                value='fakedoi',
            ),
        )
        assert res.status_code == 404

    def test_qatest_doesnt_make_dois(self):
        self.node.add_tag('qatest', auth=Auth(self.user))
        assert not request_identifiers(self.node)
