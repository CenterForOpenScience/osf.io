# -*- coding: utf-8 -*-
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


@pytest.fixture()
def crossref_client():
    return crossref.CrossRefClient(base_url='http://test.osf.crossref.test')

@pytest.fixture()
def preprint():
    node_license = NodeLicense.objects.get(name="CC-By Attribution 4.0 International")
    user = AuthUserFactory()
    provider = PreprintProviderFactory()
    provider.doi_prefix = '10.31219'
    provider.save()
    node = ProjectFactory(creator=user, preprint_article_doi='10.31219/FK2osf.io/test!')
    license_details = {
        'id': node_license.license_id,
        'year': '2017',
        'copyrightHolders': ['Jeff Hardy', 'Matt Hardy']
    }
    preprint = PreprintFactory(provider=provider, project=node, is_published=True, license_details=license_details)
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
        contributors = root.find(".//{%s}contributors" % crossref.CROSSREF_NAMESPACE)
        assert len(contributors.getchildren()) == len(preprint.node.visible_contributors)

        assert root.find(".//{%s}group_title" % crossref.CROSSREF_NAMESPACE).text == preprint.provider.name
        assert root.find('.//{%s}title' % crossref.CROSSREF_NAMESPACE).text == preprint.node.title
        assert root.find('.//{%s}item_number' % crossref.CROSSREF_NAMESPACE).text == 'osf.io/{}'.format(preprint._id)
        assert root.find('.//{%s}abstract/' % crossref.JATS_NAMESPACE).text == preprint.node.description
        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS).text == 'https://creativecommons.org/licenses/by/4.0/legalcode'
        assert root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS).get('start_date') == preprint.date_published.strftime('%Y-%m-%d')

        assert root.find('.//{%s}intra_work_relation' % crossref.CROSSREF_RELATIONS).text == preprint.node.preprint_article_doi
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

        with mock.patch('osf.models.PreprintService.get_doi_client') as mock_get_doi_client:
            mock_get_doi_client.return_value = crossref_client
            preprint.node.is_public = False
            preprint.node.save()

        crossref_xml = crossref_client.build_metadata(preprint, status='unavailable')
        root = lxml.etree.fromstring(crossref_xml)

        # body
        assert not root.find(".//{%s}contributors" % crossref.CROSSREF_NAMESPACE)

        assert root.find(".//{%s}group_title" % crossref.CROSSREF_NAMESPACE).text == preprint.provider.name
        assert not root.find('.//{%s}title' % crossref.CROSSREF_NAMESPACE).text
        assert not root.find('.//{%s}abstract/' % crossref.JATS_NAMESPACE)
        assert not root.find('.//{%s}license_ref' % crossref.CROSSREF_ACCESS_INDICATORS)

        assert root.find('.//{%s}doi' % crossref.CROSSREF_NAMESPACE).text == settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)
        assert not root.find('.//{%s}resource' % crossref.CROSSREF_NAMESPACE)
