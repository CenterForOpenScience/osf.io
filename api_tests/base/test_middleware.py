from corsheaders.middleware import CorsMiddleware
from django.http import HttpResponse
from urllib.parse import urlparse
from unittest import mock
from rest_framework.test import APIRequestFactory
from django.test.utils import override_settings

from api.base import settings as api_settings
from website.util import api_v2_url
from django.conf import settings
from tests.base import ApiTestCase
from osf_tests import factories


class MiddlewareTestCase(ApiTestCase):
    MIDDLEWARE = None

    def setUp(self):
        super().setUp()
        self.middleware = self.MIDDLEWARE(lambda _: HttpResponse())
        self.mock_response = mock.Mock()
        self.request_factory = APIRequestFactory()


class TestCorsMiddleware(MiddlewareTestCase):
    MIDDLEWARE = CorsMiddleware

    @override_settings(CORS_ORIGIN_ALLOW_ALL=False)
    def test_institutions_added_to_cors_whitelist(self):
        url = api_v2_url('users/me/')
        domain = urlparse('https://dinosaurs.sexy')
        factories.InstitutionFactory(
            domains=[domain.netloc.lower()],
            name='Institute for Sexy Lizards'
        )
        api_settings.load_origins_whitelist()
        settings.CORS_ORIGIN_WHITELIST = list(set(settings.CORS_ORIGIN_WHITELIST) | set(api_settings.ORIGINS_WHITELIST))
        request = self.request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = self.middleware(request)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()

    @override_settings(CORS_ORIGIN_ALLOW_ALL=False)
    def test_preprintproviders_added_to_cors_whitelist(self):
        url = api_v2_url('users/me/')
        domain = urlparse('https://dinoprints.sexy')
        factories.PreprintProviderFactory(
            domain=domain.geturl().lower(),
            _id='DinoXiv'
        )
        api_settings.load_origins_whitelist()
        settings.CORS_ORIGIN_WHITELIST = list(set(settings.CORS_ORIGIN_WHITELIST) | set(api_settings.ORIGINS_WHITELIST))
        request = self.request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = self.middleware(request)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()

    @override_settings(CORS_ORIGIN_ALLOW_ALL=False)
    def test_cross_origin_request_with_cookies_does_not_get_cors_headers(self):
        url = api_v2_url('users/me/')
        domain = urlparse('https://dinosaurs.sexy')
        request = self.request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        with mock.patch.object(request, 'COOKIES', True):
            response = self.middleware(request)
        assert 'Access-Control-Allow-Origin' not in response

    @override_settings(CORS_ORIGIN_ALLOW_ALL=False)
    def test_cross_origin_request_with_Authorization_gets_cors_headers(self):
        url = api_v2_url('users/me/')
        domain = urlparse('https://dinosaurs.sexy')
        request = self.request_factory.get(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_AUTHORIZATION='Bearer aqweqweohuweglbiuwefq'
        )
        api_settings.load_origins_whitelist()
        settings.CORS_ORIGIN_WHITELIST = list(set(settings.CORS_ORIGIN_WHITELIST) | set(api_settings.ORIGINS_WHITELIST))
        response = self.middleware(request)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()

    @override_settings(CORS_ORIGIN_ALLOW_ALL=False)
    def test_cross_origin_request_with_Authorization_and_cookie_does_not_get_cors_headers(
            self):
        url = api_v2_url('users/me/')
        domain = urlparse('https://dinosaurs.sexy')
        request = self.request_factory.get(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_AUTHORIZATION='Bearer aqweqweohuweglbiuwefq'
        )
        api_settings.load_origins_whitelist()
        settings.CORS_ORIGIN_WHITELIST = list(set(settings.CORS_ORIGIN_WHITELIST) | set(api_settings.ORIGINS_WHITELIST))
        with mock.patch.object(request, 'COOKIES', True):
            response = self.middleware(request)
        assert 'Access-Control-Allow-Origin' not in response

    @override_settings(CORS_ORIGIN_ALLOW_ALL=False)
    def test_non_institution_preflight_request_requesting_authorization_header_gets_cors_headers(
            self):
        url = api_v2_url('users/me/')
        domain = urlparse('https://dinosaurs.sexy')
        request = self.request_factory.options(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization'
        )
        api_settings.load_origins_whitelist()
        settings.CORS_ORIGIN_WHITELIST = list(set(settings.CORS_ORIGIN_WHITELIST) | set(api_settings.ORIGINS_WHITELIST))
        response = self.middleware(request)
        assert response['Access-Control-Allow-Origin'] == domain.geturl()
