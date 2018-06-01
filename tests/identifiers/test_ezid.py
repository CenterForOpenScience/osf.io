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


@pytest.mark.django_db
class TestEZIDClient(OsfTestCase):

    def setUp(self):
        super(TestEZIDClient, self).setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.client = EzidClient(base_url='https://test.ezid.osf.io', prefix=settings.EZID_DOI_NAMESPACE.replace('doi:', ''))

    @responses.activate
    def test_create_identifiers_not_exists_ezid(self):
        guid = self.registration._id
        url = furl.furl(self.client.base_url)
        doi = settings.DOI_FORMAT.format(prefix=settings.EZID_DOI_NAMESPACE, guid=guid).replace('doi:', '')
        url.path.segments += ['id', doi]
        responses.add(
            responses.Response(
                responses.PUT,
                url.url,
                body=to_anvl({
                    'success': '{doi}osf.io/{ident} | {ark}osf.io/{ident}'.format(
                        doi=settings.EZID_DOI_NAMESPACE,
                        ark=settings.EZID_ARK_NAMESPACE,
                        ident=guid,
                    ),
                }),
                status=201,
            )
        )
        with mock.patch('osf.models.Registration.get_doi_client') as mock_get_doi:
            mock_get_doi.return_value = self.client
            res = self.app.post(
                self.registration.api_url_for('node_identifiers_post'),
                auth=self.user.auth,
            )
        self.registration.reload()
        assert_equal(
            res.json['doi'],
            self.registration.get_identifier_value('doi')
        )

        assert_equal(res.status_code, 201)


    @responses.activate
    def test_create_identifiers_exists_ezid(self):
        guid = self.registration._id
        doi = settings.DOI_FORMAT.format(prefix=settings.EZID_DOI_NAMESPACE, guid=guid).replace('doi:', '')
        url = furl.furl(self.client.base_url)
        url.path.segments += ['id', doi]
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
        with mock.patch('osf.models.Registration.get_doi_client') as mock_get_doi:
            mock_get_doi.return_value = self.client
            res = self.app.post(
                    self.registration.api_url_for('node_identifiers_post'),
                    auth=self.user.auth,
            )
        self.registration.reload()
        assert_equal(
            res.json['doi'],
            self.registration.get_identifier_value('doi')
        )
        assert_equal(
            res.json['ark'],
            self.registration.get_identifier_value('ark')
        )
        assert_equal(res.status_code, 201)

    @responses.activate
    def test_get_by_identifier(self):
        self.registration.set_identifier_value('doi', 'FK424601')
        self.registration.set_identifier_value('ark', 'fk224601')
        res_doi = self.app.get(
            self.registration.web_url_for(
                'get_referent_by_identifier',
                category='doi',
                value=self.registration.get_identifier_value('doi'),
            ),
        )
        assert_equal(res_doi.status_code, 302)
        assert_urls_equal(res_doi.headers['Location'], self.registration.absolute_url)
        res_ark = self.app.get(
            self.registration.web_url_for(
                'get_referent_by_identifier',
                category='ark',
                value=self.registration.get_identifier_value('ark'),
            ),
        )
        assert_equal(res_ark.status_code, 302)
        assert_urls_equal(res_ark.headers['Location'], self.registration.absolute_url)

    @responses.activate
    def test_get_by_identifier_not_found(self):
        self.registration.set_identifier_value('doi', 'FK424601')
        res = self.app.get(
            self.registration.web_url_for(
                'get_referent_by_identifier',
                category='doi',
                value='fakedoi',
            ),
            expect_errors=True,
        )
        assert_equal(res.status_code, 404)
