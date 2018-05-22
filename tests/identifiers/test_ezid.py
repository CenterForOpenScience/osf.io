import furl
import mock
import pytest
import responses

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.test_addons import assert_urls_equal
from osf_tests.factories import AuthUserFactory, RegistrationFactory

from website import settings
from website.app import init_addons
from website.identifiers.utils import to_anvl
from website.identifiers.clients import EzidClient

init_addons(settings)


@pytest.mark.django_db
class TestEZIDClient(OsfTestCase):

    def setUp(self):
        super(TestEZIDClient, self).setUp()
        self.user = AuthUserFactory()
        self.node = RegistrationFactory(creator=self.user, is_public=True)

    @responses.activate
    @mock.patch('website.identifiers.utils.get_doi_client', return_value=EzidClient())
    def test_create_identifiers_not_exists_ezid(self, mock_client):
        identifier = self.node._id
        url = furl.furl('https://ezid.cdlib.org/id')
        doi = settings.DOI_FORMAT.format(prefix=settings.EZID_DOI_NAMESPACE, guid=identifier)
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
    @mock.patch('website.identifiers.utils.get_doi_client', return_value=EzidClient())
    def test_create_identifiers_exists_ezid(self, mock_client):
        identifier = self.node._id
        doi = settings.DOI_FORMAT.format(prefix=settings.EZID_DOI_NAMESPACE, guid=identifier)
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

    @responses.activate
    @mock.patch('website.identifiers.utils.get_doi_client', return_value=EzidClient())
    def test_get_by_identifier(self, mock_client):
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

    @responses.activate
    @mock.patch('website.identifiers.utils.get_doi_client', return_value=EzidClient())
    def test_get_by_identifier_not_found(self, mock_client):
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


