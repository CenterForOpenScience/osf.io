# -*- coding: utf-8 -*-
import mock
import lxml
import pytest
import responses
from nose.tools import *  # noqa

from website import settings
from website.app import init_addons

from tests.identifers.fixtures import (
    preprint,
    crossref_client,
    crossref_success_response,
    crossref_preprint_metadata
)

init_addons(settings)


@pytest.mark.django_db
class TestCrossRefClient:

    @responses.activate
    @mock.patch('website.identifiers.clients.crossref_client.CrossRefClient.BASE_URL', 'https://test.test.osf.io')
    def test_crossref_create_identifiers(self, crossref_client, crossref_preprint_metadata, crossref_success_response):
        responses.add(
            responses.Response(
                responses.POST,
                'https://test.test.osf.io',
                body=crossref_success_response,
                content_type='text/html;charset=ISO-8859-1',
                status=200
            )
        )
        res = crossref_client.create_identifier(doi='10.123test/FK2osf.io/jf36m',
                                                metadata=crossref_preprint_metadata)

        assert res['doi'] == '10.123test/FK2osf.io/jf36m'

    @responses.activate
    @mock.patch('website.identifiers.clients.crossref_client.CrossRefClient.BASE_URL', 'https://test.test.osf.io')
    def test_crossref_change_status_identifier(self,  crossref_client, crossref_preprint_metadata, crossref_success_response):
        responses.add(
            responses.Response(
                responses.POST,
                'https://test.test.osf.io',
                body=crossref_success_response,
                content_type='text/html;charset=ISO-8859-1',
                status=200
            )
        )
        res = crossref_client.change_status_identifier(status=None,
                                                       metadata=crossref_preprint_metadata,
                                                       identifier='10.123test/FK2osf.io/jf36m')

        assert res['doi'] == '10.123test/FK2osf.io/jf36m'

    def test_crossref_build_doi(self, crossref_client, preprint):
        doi_prefix = preprint.provider.doi_prefix

        assert crossref_client.build_doi(preprint) == '{}/FK2osf.io/{}'.format(doi_prefix, preprint._id)

    def test_crossref_build_metadata(self, crossref_client, preprint):
        test_email = 'test-email'
        with mock.patch('website.settings.CROSSREF_DEPOSITOR_EMAIL', test_email):
            crossref_xml = crossref_client.build_metadata(preprint, pretty_print=True)
        root = lxml.etree.fromstring(crossref_xml)

        # header
        assert root.find('.//{%s}doi_batch_id' % settings.CROSSREF_NAMESPACE).text == preprint._id
        assert root.find('.//{%s}depositor_name' % settings.CROSSREF_NAMESPACE).text == settings.CROSSREF_DEPOSITOR_NAME
        assert root.find('.//{%s}email_address' % settings.CROSSREF_NAMESPACE).text == test_email

        # body
        contributors = root.find(".//{%s}contributors" % settings.CROSSREF_NAMESPACE)
        assert len(contributors.getchildren()) == len(preprint.node.visible_contributors)

        assert root.find(".//{%s}group_title" % settings.CROSSREF_NAMESPACE).text == preprint.provider.name
        assert root.find('.//{%s}title' % settings.CROSSREF_NAMESPACE).text == preprint.node.title
        assert root.find('.//{%s}item_number' % settings.CROSSREF_NAMESPACE).text == 'osf.io/{}'.format(preprint._id)
        assert root.find('.//{%s}abstract/' % settings.JATS_NAMESPACE).text == preprint.node.description
        assert root.find('.//{%s}license_ref' % settings.CROSSREF_ACCESS_INDICATORS).text == 'https://creativecommons.org/licenses/by/4.0/legalcode'
        assert root.find('.//{%s}license_ref' % settings.CROSSREF_ACCESS_INDICATORS).get('start_date') == preprint.date_published.strftime('%Y-%m-%d')

        assert root.find('.//{%s}intra_work_relation' % settings.CROSSREF_RELATIONS).text == preprint.node.preprint_article_doi
        assert root.find('.//{%s}doi' % settings.CROSSREF_NAMESPACE).text == settings.CROSSREF_DOI_FORMAT.format(namespace=preprint.provider.doi_prefix, guid=preprint._id)
        assert root.find('.//{%s}resource' % settings.CROSSREF_NAMESPACE).text == settings.DOMAIN + preprint._id

        metadata_date_parts = [elem.text for elem in root.find('.//{%s}posted_date' % settings.CROSSREF_NAMESPACE)]
        preprint_date_parts = preprint.date_published.strftime('%Y-%m-%d').split('-')
        assert set(metadata_date_parts) == set(preprint_date_parts)