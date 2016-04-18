# -*- coding: utf-8 -*-

from tests.base import ApiTestCase, fake

from urlparse import urlparse
import mock
from nose.tools import *  # flake8: noqa
from rest_framework.test import APIRequestFactory

from website.util import api_v2_url
from api.base import settings
from api.base.middleware import TokuTransactionMiddleware, CorsMiddleware
from tests.base import ApiTestCase
from tests import factories

class MiddlewareTestCase(ApiTestCase):
    MIDDLEWARE = None

    def setUp(self):
        super(MiddlewareTestCase, self).setUp()
        self.middleware = self.MIDDLEWARE()
        self.mock_response = mock.Mock()
        self.request_factory = APIRequestFactory()

class TestMiddlewareRollback(MiddlewareTestCase):
    MIDDLEWARE = TokuTransactionMiddleware

    @mock.patch('framework.transactions.handlers.commands')
    def test_400_error_causes_rollback(self, mock_commands):

        self.mock_response.status_code = 400
        self.middleware.process_response(mock.Mock(), self.mock_response)

        assert_true(mock_commands.rollback.called)

    @mock.patch('framework.transactions.handlers.commands')
    def test_200_OK_causes_commit(self, mock_commands):

        self.mock_response.status_code = 200
        self.middleware.process_response(mock.Mock(), self.mock_response)

        assert_true(mock_commands.commit.called)

class TestCorsMiddleware(MiddlewareTestCase):
    MIDDLEWARE = CorsMiddleware

    def test_institutions_added_to_cors_whitelist(self):
        url = api_v2_url('users/me/')
        domain = urlparse("https://dinosaurs.sexy")
        institution = factories.InstitutionFactory(
            institution_domains=[domain.netloc.lower()],
            title="Institute for Sexy Lizards"
        )
        CorsMiddleware.INSTITUTION_ORIGINS_WHITELIST = CorsMiddleware.INSTITUTION_ORIGINS_WHITELIST + (domain.netloc.lower(),)
        request = self.request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = {}
        self.middleware.process_request(request)
        processed = self.middleware.process_response(request, response)
        assert_equal(response['Access-Control-Allow-Origin'], domain.geturl())

    def test_cross_origin_request_with_cookies_does_not_get_cors_headers(self):
        url = api_v2_url('users/me/')
        domain = urlparse("https://dinosaurs.sexy")
        request = self.request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = {}
        with mock.patch.object(request, 'COOKIES', True):
            self.middleware.process_request(request)
            processed = self.middleware.process_response(request, response)
        assert_not_in('Access-Control-Allow-Origin', response)

    def test_cross_origin_request_with_Authorization_gets_cors_headers(self):
        url = api_v2_url('users/me/')
        domain = urlparse("https://dinosaurs.sexy")
        request = self.request_factory.get(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_AUTHORIZATION="Bearer aqweqweohuweglbiuwefq"
        )
        response = {}
        self.middleware.process_request(request)
        processed = self.middleware.process_response(request, response)
        assert_equal(response['Access-Control-Allow-Origin'], domain.geturl())

    def test_cross_origin_request_with_Authorization_and_cookie_does_not_get_cors_headers(self):
        url = api_v2_url('users/me/')
        domain = urlparse("https://dinosaurs.sexy")
        request = self.request_factory.get(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_AUTHORIZATION="Bearer aqweqweohuweglbiuwefq"
        )
        response = {}
        with mock.patch.object(request, 'COOKIES', True):
            self.middleware.process_request(request)
            processed = self.middleware.process_response(request, response)
        assert_not_in('Access-Control-Allow-Origin', response)

    def test_non_institution_preflight_request_requesting_authorization_header_gets_cors_headers(self):        
        url = api_v2_url('users/me/')
        domain = urlparse("https://dinosaurs.sexy")
        request = self.request_factory.options(
            url,
            HTTP_ORIGIN=domain.geturl(),
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization'
        )
        response = {}
        self.middleware.process_request(request)
        processed = self.middleware.process_response(request, response)
        assert_equal(response['Access-Control-Allow-Origin'], domain.geturl())

