# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import mock
import lxml
import pytest
import responses
from nose.tools import *  # noqa

from website import settings
from website.identifiers.clients import crossref

from osf.models import NodeLicense
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    PreprintProviderFactory,
    AuthUserFactory
)
from framework.flask import rm_handlers
from framework.auth.core import Auth
from framework.auth.utils import impute_names


@pytest.fixture()
def crossref_client():
    return crossref.CrossRefClient(base_url='http://test.osf.crossref.test')

@pytest.fixture()
def preprint():
    node_license = NodeLicense.objects.get(name='CC-By Attribution 4.0 International')
    user = AuthUserFactory()
    provider = PreprintProviderFactory()
    provider.doi_prefix = '10.31219'
    provider.save()
    license_details = {
        'id': node_license.license_id,
        'year': '2017',
        'copyrightHolders': ['Jeff Hardy', 'Matt Hardy']
    }
    preprint = PreprintFactory(provider=provider, article_doi='10.31219/FK2osf.io/test!', is_published=True, license_details=license_details)
    preprint.license.node_license.url = 'https://creativecommons.org/licenses/by/4.0/legalcode'
    return preprint

@pytest.fixture()
def crossref_success_response():
    return """
        \n\n\n\n<html>\n<head><title>SUCCESS</title>\n</head>\n<body>\n<h2>SUCCESS</h2>\n<p>
        Your batch submission was successfully received.</p>\n</body>\n</html>\n
        """


@pytest.mark.django_db
class TestCrossRefClient:

    @responses.activate
    def test_crossref_create_identifiers(self, preprint, crossref_client, crossref_success_response):
        responses.add(
            responses.Response(
                responses.POST,
                crossref_client.base_url,
                body=crossref_success_response,
                content_type='text/html;charset=ISO-8859-1',
                status=200,
            ),
        )
        res = crossref_client.create_identifier(preprint=preprint, category='doi')
        doi = settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)

        assert res['doi'] == doi

    @responses.activate
    def test_crossref_update_identifier(self,  preprint, crossref_client, crossref_success_response):
        responses.add(
            responses.Response(
                responses.POST,
                crossref_client.base_url,
                body=crossref_success_response,
                content_type='text/html;charset=ISO-8859-1',
                status=200
            )
        )
        res = crossref_client.update_identifier(preprint, category='doi')
        doi = settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)

        assert res['doi'] == doi

    def test_crossref_build_doi(self, crossref_client, preprint):
        doi_prefix = preprint.provider.doi_prefix

        assert crossref_client.build_doi(preprint) == settings.DOI_FORMAT.format(prefix=doi_prefix, guid=preprint._id)

    def test_crossref_build_metadata(self, crossref_client, preprint):
        test_email = 'test-email@osf.io'
        with mock.patch('website.settings.CROSSREF_DEPOSITOR_EMAIL', test_email):
            crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)

        # header
        assert root.find('.//{%s}doi_batch_id' % crossref.CROSSREF_NAMESPACE).text == preprint._id
        assert root.find('.//{%s}depositor_name' % crossref.CROSSREF_NAMESPACE).text == crossref.CROSSREF_DEPOSITOR_NAME
        assert root.find('.//{%s}email_address' % crossref.CROSSREF_NAMESPACE).text == test_email

        # body
        contributors = root.find('.//{%s}contributors' % crossref.CROSSREF_NAMESPACE)
        assert len(contributors.getchildren()) == len(preprint.visible_contributors)

        assert root.find('.//{%s}group_title' % crossref.CROSSREF_NAMESPACE).text == preprint.provider.name
        assert root.find('.//{%s}title' % crossref.CROSSREF_NAMESPACE).text == preprint.title
        assert root.find('.//{%s}item_number' % crossref.CROSSREF_NAMESPACE).text == 'osf.io/{}'.format(preprint._id)
        assert root.find('.//{%s}abstract/' % crossref.JATS_NAMESPACE).text == preprint.description
        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS).text == 'https://creativecommons.org/licenses/by/4.0/legalcode'
        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS).get('start_date') == preprint.date_published.strftime('%Y-%m-%d')

        assert root.find('.//{%s}intra_work_relation' % crossref.CROSSREF_RELATIONS).text == preprint.article_doi
        assert root.find('.//{%s}doi' % crossref.CROSSREF_NAMESPACE).text == settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)
        assert root.find('.//{%s}resource' % crossref.CROSSREF_NAMESPACE).text == settings.DOMAIN + preprint._id

        metadata_date_parts = [elem.text for elem in root.find('.//{%s}posted_date' % crossref.CROSSREF_NAMESPACE)]
        preprint_date_parts = preprint.date_published.strftime('%Y-%m-%d').split('-')
        assert set(metadata_date_parts) == set(preprint_date_parts)

    @responses.activate
    def test_metadata_for_deleted_node(self, crossref_client, preprint):
        responses.add(
            responses.Response(
                responses.POST,
                crossref_client.base_url,
                body=crossref_success_response,
                content_type='text/html;charset=ISO-8859-1',
                status=200
            )
        )

        with mock.patch('osf.models.Preprint.get_doi_client') as mock_get_doi_client:
            mock_get_doi_client.return_value = crossref_client
            preprint.is_public = False
            preprint.save()

        crossref_xml = crossref_client.build_metadata(preprint, status='unavailable')
        root = lxml.etree.fromstring(crossref_xml)

        # body
        assert not root.find('.//{%s}contributors' % crossref.CROSSREF_NAMESPACE)

        assert root.find('.//{%s}group_title' % crossref.CROSSREF_NAMESPACE).text == preprint.provider.name
        assert not root.find('.//{%s}title' % crossref.CROSSREF_NAMESPACE).text
        assert not root.find('.//{%s}abstract/' % crossref.JATS_NAMESPACE)
        assert not root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS)

        assert root.find('.//{%s}doi' % crossref.CROSSREF_NAMESPACE).text == settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)
        assert not root.find('.//{%s}resource' % crossref.CROSSREF_NAMESPACE)

    def test_process_crossref_name(self, crossref_client):
        contributor = AuthUserFactory()

        # Given name and no family name
        contributor.given_name = 'Hey'
        contributor.family_name = ''
        contributor.save()
        meta = crossref_client._process_crossref_name(contributor)
        imputed_names = impute_names(contributor.fullname)
        assert meta == {'surname': imputed_names['family'], 'given_name': imputed_names['given']}

        # Just one name
        contributor.fullname = 'Ke$ha'
        contributor.given_name = ''
        contributor.family_name = ''
        contributor.save()
        meta = crossref_client._process_crossref_name(contributor)
        assert meta == {'surname': contributor.fullname}

        # Number and ? in given name
        contributor.fullname = 'Scotty2Hotty? Ronald Garland II'
        contributor.given_name = ''
        contributor.family_name = ''
        contributor.save()
        meta = crossref_client._process_crossref_name(contributor)
        assert meta == {'given_name': 'ScottyHotty Ronald', 'surname': 'Garland', 'suffix': 'II'}

        # Long suffix is truncated to 10 characters
        long_suffix = 'PhD MD Esq MPH IV'
        contributor.given_name = 'Mark'
        contributor.family_name = 'Henry'
        contributor.suffix = long_suffix
        contributor.save()
        meta = crossref_client._process_crossref_name(contributor)
        assert meta['suffix'] == long_suffix[:crossref.CROSSREF_SUFFIX_LIMIT]

        # Long given_names and surnames are truncated to limit
        long_given = 'Maaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaark'
        long_surname = 'Henryyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
        contributor.given_name = long_given
        contributor.family_name = long_surname
        contributor.save()

        meta = crossref_client._process_crossref_name(contributor)
        assert meta['given_name'] == long_given[:crossref.CROSSREF_GIVEN_NAME_LIMIT]
        assert meta['surname'] == long_surname[:crossref.CROSSREF_SURNAME_LIMIT]

        # Unparsable given or surname just returns fullname as surname
        unparsable_fullname = 'Author (name withheld until double-blind peer review completes and this name is also really long)'
        contributor.given_name = ''
        contributor.family_name = ''
        contributor.fullname = unparsable_fullname
        contributor.save()

        meta = crossref_client._process_crossref_name(contributor)
        assert meta == {'surname': unparsable_fullname[:crossref.CROSSREF_SURNAME_LIMIT]}

    def test_metadata_for_single_name_contributor_only_has_surname(self, crossref_client, preprint):
        contributor = preprint.creator
        contributor.fullname = 'Madonna'
        contributor.given_name = ''
        contributor.family_name = ''
        contributor.save()

        crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)
        contributors = root.find('.//{%s}contributors' % crossref.CROSSREF_NAMESPACE)

        assert contributors.find('.//{%s}surname' % crossref.CROSSREF_NAMESPACE).text == 'Madonna'
        assert not contributors.find('.//{%s}given_name' % crossref.CROSSREF_NAMESPACE)

    def test_metadata_contributor_orcid(self, crossref_client, preprint):
        ORCID = '1234-5678-2345-6789'

        # verified ORCID
        contributor = preprint.creator
        contributor.external_identity = {
            'ORCID': {
                ORCID: 'VERIFIED'
            }
        }
        contributor.save()

        crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)
        contributors = root.find('.//{%s}contributors' % crossref.CROSSREF_NAMESPACE)

        assert contributors.find('.//{%s}ORCID' % crossref.CROSSREF_NAMESPACE).text == 'https://orcid.org/{}'.format(ORCID)
        assert contributors.find('.//{%s}ORCID' % crossref.CROSSREF_NAMESPACE).attrib == {'authenticated': 'true'}

        # unverified (only in profile)
        contributor.external_identity = {}
        contributor.social = {
            'orcid': ORCID
        }
        contributor.save()

        crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)
        contributors = root.find('.//{%s}contributors' % crossref.CROSSREF_NAMESPACE)

        assert contributors.find('.//{%s}ORCID' % crossref.CROSSREF_NAMESPACE) is None

    def test_metadata_none_license_update(self, crossref_client, preprint):
        crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)

        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS).text == 'https://creativecommons.org/licenses/by/4.0/legalcode'
        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS).get('start_date') == preprint.date_published.strftime('%Y-%m-%d')

        license_detail = {
            'copyrightHolders': ['The Carters'],
            'id': 'NONE',
            'year': '2018'
        }

        preprint.set_preprint_license(license_detail, Auth(preprint.creator), save=True)

        crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)

        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS) is None
        assert root.find('.//{%s}program' % crossref.CROSSREF_ACCESS_INDICATORS).getchildren() == []

    def test_metadata_for_non_included_relation(self, crossref_client, preprint):
        crossref_xml = crossref_client.build_metadata(preprint)
        root = lxml.etree.fromstring(crossref_xml)
        assert root.find('.//{%s}intra_work_relation' % crossref.CROSSREF_RELATIONS).text == preprint.article_doi

        xml_without_relation = crossref_client.build_metadata(preprint, include_relation=False)
        root_without_relation = lxml.etree.fromstring(xml_without_relation)
        assert root_without_relation.find('.//{%s}intra_work_relation' % crossref.CROSSREF_RELATIONS) is None
