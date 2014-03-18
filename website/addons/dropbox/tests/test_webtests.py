# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp
from website.app import init_app
from website.util import web_url_for, api_url_for
from website.project.model import ensure_schemas
from tests.base import DbTestCase
from tests.factories import AuthUserFactory

app = init_app(set_backends=False, routes=True)

# TODO(sloria): Move to tests.base

class URLLookup(object):

    def __init__(self, app):
        self.app = app

    def web_url_for(self, view_name, *args, **kwargs):
        with self.app.test_request_context():
            url = web_url_for(view_name, *args, **kwargs)
        return url

    def api_url_for(self, view_name, *args, **kwargs):
        with self.app.test_request_context():
            url = api_url_for(view_name, *args, **kwargs)
        return url

    def __call__(self, type_, view_name, *args, **kwargs):
        if type_ == 'web':
            return self.web_url_for(view_name, *args, **kwargs)
        else:
            return self.api_url_for(view_name, *args, **kwargs)


lookup = URLLookup(app)


class TestDropboxIntegration(DbTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        # User is logged in
        self.app.authenticate(*self.user.auth)

    def test_user_can_create_access_token_on_settings_page(self):
        with app.test_request_context():
            url = web_url_for('profile_settings')
        res = self.app.get(url)

        assert_not_in('Create Access Token', res)
        form = res.forms['selectAddonsForm']
        form['dropbox'] = True
        res = form.submit()
        assert_equal(res.status_code, 200)

        assert_in('Create Access Token', res)

    def test_cant_start_oauth_if_already_authorized(self):
        # User already has dropbox authorized
        self.user.add_addon('dropbox')
        self.user.save()
        settings = self.user.get_addon('dropbox')
        settings.access_token = 'abc123foobarbaz'
        settings.save()
        assert_true(self.user.get_addon('dropbox').has_auth)
        # Tries to start oauth again
        url = lookup('api', 'dropbox_oauth_start__user')
        res = self.app.get(url).follow()

        # Is redirected back to settings page
        assert_equal(res.request.path,
            lookup('web', 'profile_settings'))
