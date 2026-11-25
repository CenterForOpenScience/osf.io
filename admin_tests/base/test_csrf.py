from copy import deepcopy

import pytest
from webpack_loader.loaders import WebpackLoader

from django.test import Client
from django.urls import reverse

from admin.base import settings as admin_settings


@pytest.mark.django_db
@pytest.mark.urls('admin.base.urls')
class TestAdminCSRF:

    @pytest.fixture
    def admin_client(self, settings, monkeypatch):
        monkeypatch.setattr(WebpackLoader, 'get_bundle', lambda self, bundle_name: [])
        # Admin templates need webpack_loader, which isn't in the API test settings.
        templates = deepcopy(admin_settings.TEMPLATES)
        templates[0]['OPTIONS']['libraries'] = {
            'webpack_loader': 'webpack_loader.templatetags.webpack_loader',
        }
        settings.MIDDLEWARE = admin_settings.MIDDLEWARE
        settings.TEMPLATES = templates
        settings.WEBPACK_LOADER = admin_settings.WEBPACK_LOADER
        settings.CSRF_COOKIE_NAME = admin_settings.CSRF_COOKIE_NAME
        settings.CSRF_COOKIE_HTTPONLY = admin_settings.CSRF_COOKIE_HTTPONLY
        return Client(enforce_csrf_checks=True, HTTP_REFERER='https://testserver/')

    @pytest.mark.parametrize('secure', [False, True])
    def test_login_form_with_httponly_csrf_cookie(self, admin_client, settings, secure):
        settings.CSRF_COOKIE_SECURE = secure
        url = reverse('auth:login')
        response = admin_client.get(url, secure=secure)

        assert response.status_code == 200
        cookie = response.cookies[admin_settings.CSRF_COOKIE_NAME]
        assert bool(cookie['secure']) == secure
        assert cookie['httponly']

        assert admin_client.post(url, secure=secure).status_code == 403

        response = admin_client.post(url, {
            'csrfmiddlewaretoken': str(response.context['csrf_token']),
        }, secure=secure)
        assert response.status_code == 302
        assert response.url == url
