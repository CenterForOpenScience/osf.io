# -*- coding: utf-8 -*-
import pytest

from django.http import HttpResponse
from tests.base import ApiTestCase, fake

from urlparse import urlparse
import mock
from nose.tools import *  # flake8: noqa
from rest_framework.test import APIRequestFactory

from website.util import api_v2_url
from api.base import settings
from api.base.middleware import CorsMiddleware
from tests.base import ApiTestCase
from osf_tests import factories

class MiddlewareTestCase(ApiTestCase):
    MIDDLEWARE = None

    def setUp(self):
        super(MiddlewareTestCase, self).setUp()
        self.middleware = self.MIDDLEWARE()
        self.mock_response = mock.Mock()
        self.request_factory = APIRequestFactory()


class TestCorsMiddleware(MiddlewareTestCase):
    MIDDLEWARE = CorsMiddleware

    def test_institutions_added_to_cors_whitelist(self):
        url = api_v2_url('users/me/')
        domain = urlparse("https://dinosaurs.sexy")
        institution = factories.InstitutionFactory(
            domains=[domain.netloc.lower()],
            name="Institute for Sexy Lizards"
        )
        settings.load_institutions()
        request = self.request_factory.get(url, HTTP_ORIGIN=domain.geturl())
        response = HttpResponse()
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
        response = HttpResponse()
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
        response = HttpResponse()
        self.middleware.process_request(request)
        processed = self.middleware.process_response(request, response)
        assert_equal(response['Access-Control-Allow-Origin'], domain.geturl())
