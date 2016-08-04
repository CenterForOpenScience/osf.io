import httplib as http

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import campaigns, views as auth_views, cas
from website.util import web_url_for
from website.project.model import ensure_schemas
from tests import factories
from tests.base import OsfTestCase
from tests.utils import mock_auth


class TestCampaignsPrereg(OsfTestCase):

    def setUp(self):
        super(TestCampaignsPrereg, self).setUp()
        self.url_login = web_url_for('auth_login', campaign='prereg')
        self.url_register = web_url_for('auth_register', campaign='prereg')
        self.url_landing_page = campaigns.campaign_url_for('prereg')
        self.user = factories.AuthUserFactory()

    def test_auth_register_with_prereg_logged_in(self):
        resp = self.app.get(self.url_register, auth=self.user.auth)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(self.url_landing_page, resp.headers['Location'])

    def test_auth_register_with_prereg_logged_out(self):
        resp = self.app.get(self.url_register)
        assert_equal(resp.status_code, http.OK)
        assert_in('Preregistration Challenge', resp)
        assert_in('You must log in to access this resource.', resp)

    def test_auth_login_with_prereg_logged_in(self):
        resp = self.app.get(self.url_login, auth=self.user.auth)
        assert_equal(resp.status_code, http.FOUND)
        assert_in(self.url_register, resp.headers['Location'])

    def test_auth_login_with_prereg_logged_out(self):
        resp = self.app.get(self.url_login)
        assert_equal(resp.status_code, http.FOUND)
        assert_in(self.url_register, resp.headers['Location'])

    def test_auth_prereg_landing_page_logged_in(self):
        ensure_schemas()
        resp = self.app.get(self.url_landing_page, auth=self.user.auth)
        assert_equal(resp.status_code, http.OK)
        assert_in('Welcome to the Preregistration Challenge!', resp)

    def test_auth_prereg_landing_page_logged_out(self):
        resp = self.app.get(self.url_landing_page)
        assert_equal(resp.status_code, http.FOUND)
        assert_in(cas.get_login_url(self.url_landing_page), resp.headers['Location'])

    def test_confirm_email_get_with_campaign(self):
        user = factories.UnconfirmedUserFactory()
        user.system_tags.append(campaigns.CAMPAIGNS['prereg']['system_tag'])
        user.save()
        token = user.get_confirmation_token(user.username)
        print token
        kwargs = {
            'uid': user._id,
        }
        with self.app.app.test_request_context(), mock_auth(user):
            res = auth_views.confirm_email_get(token, **kwargs)
            assert_equal(res.status_code, http.FOUND)
            assert_equal(res.location, campaigns.CAMPAIGNS['prereg']['redirect_url']())


class TestCampaignsCASInstitutionLogin(OsfTestCase):

    def setUp(self):
        super(TestCampaignsCASInstitutionLogin, self).setUp()
        self.url_login = web_url_for('auth_login', campaign='institution')
        self.url_register = web_url_for('auth_register', campaign='institution')
        self.service_url = web_url_for('dashboard', _absolute=True)

    def test_institution_login_not_logged_in(self):
        resp = self.app.get(self.url_login)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(cas.get_login_url(self.service_url, campaign='institution'), resp.headers['Location'])
        resp2 = self.app.get(self.url_register)
        assert_equal(resp.headers['Location'], resp2.headers['Location'])
