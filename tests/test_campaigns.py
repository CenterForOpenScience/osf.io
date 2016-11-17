import httplib as http

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import campaigns, views as auth_views, cas
from website.util import web_url_for
from website.project.model import ensure_schemas
from tests import factories
from tests.base import OsfTestCase
from tests.utils import mock_auth


# test for prereg, erpc and preprints, which follow similar auth login/register logic
class TestCampaignsAuthViews(OsfTestCase):

    def setUp(self):
        super(TestCampaignsAuthViews, self).setUp();
        self.campaigns = {
            'prereg': {
                'title_register': 'Preregistration Challenge',
                'title_landing': 'Welcome to the Prereg Challenge!'
            },
            'erpc': {
                'title_register': 'Election Research Preacceptance Competition',
                'title_landing': 'Welcome to the Election Research Preacceptance Competition!'
            },
            'osf-preprints': {
                'title_register': 'OSF Preprint Service',
                'title_landing': 'OSF Preprints'
            }
        }
        for key, value in self.campaigns.items():
            value.update({'url_login': web_url_for('auth_login', campaign=key)})
            value.update({'url_register': web_url_for('auth_register', campaign=key)})
            value.update({'url_landing': campaigns.campaign_url_for(key)})
        self.user = factories.AuthUserFactory()

    def test_campaign_register_view_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_register'], auth=self.user.auth)
            assert_equal(resp.status_code, http.FOUND)
            assert_equal(value['url_landing'], resp.headers['Location'])

    def test_campaign_register_view_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_register'])
            assert_equal(resp.status_code, http.OK)
            assert_in(value['title_register'], resp)

    def test_campaign_login_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_login'], auth=self.user.auth)
            assert_equal(resp.status_code, http.FOUND)
            assert_in(value['url_landing'], resp.headers['Location'])

    def test_campaign_login_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_login'])
            assert_equal(resp.status_code, http.FOUND)
            assert_in(value['url_register'], resp.headers['Location'])

    def test_campaign_landing_logged_in(self):
        ensure_schemas()
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_landing'], auth=self.user.auth)
            assert_equal(resp.status_code, http.OK)
            assert_in(value['title_landing'], resp)

    def test_auth_prereg_landing_page_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_landing'])
            if key == 'osf-preprints':
                assert_equal(resp.status_code, http.OK)
                assert_in(value['title_landing'], resp)
            else:
                assert_equal(resp.status_code, http.FOUND)
                assert_in(cas.get_login_url(value['url_landing']), resp.headers['Location'])


# test for registration through campaigns
class TestRegistrationThroughCampaigns(OsfTestCase):

    def setUp(self):
        super(TestRegistrationThroughCampaigns, self).setUp()

    def test_confirm_email_get_with_campaign(self):

        for key, value in campaigns.CAMPAIGNS.items():
            user = factories.UnconfirmedUserFactory()
            user.system_tags.append(campaigns.CAMPAIGNS[key]['system_tag'])
            user.save()
            token = user.get_confirmation_token(user.username)
            kwargs = {
                'uid': user._id,
            }
            with self.app.app.test_request_context(), mock_auth(user):
                res = auth_views.confirm_email_get(token, **kwargs)
                assert_equal(res.status_code, http.FOUND)
                assert_equal(res.location, campaigns.campaign_url_for(key))


# test for institution
class TestCampaignsCASInstitutionLogin(OsfTestCase):

    def setUp(self):
        super(TestCampaignsCASInstitutionLogin, self).setUp()
        self.url_login = web_url_for('auth_login', campaign='institution')
        self.url_register = web_url_for('auth_register', campaign='institution')
        self.service_url = web_url_for('dashboard', _absolute=True)

    # go to CAS institution login page if not logged in
    def test_institution_not_logged_in(self):
        resp = self.app.get(self.url_login)
        assert_equal(resp.status_code, http.FOUND)
        assert_in(cas.get_login_url(self.service_url, campaign='institution'), resp.headers['Location'])
        # register behave the same as login
        resp2 = self.app.get(self.url_register)
        assert_equal(resp.headers['Location'], resp2.headers['Location'])

    # go to target page (service url_ if logged in
    def test_institution_logged_in(self):
        resp = self.app.get(self.url_login)
        assert_equal(resp.status_code, http.FOUND)
        assert_in(self.service_url, resp.headers['Location'])
        # register behave the same as login
        resp2 = self.app.get(self.url_register)
        assert_equal(resp.headers['Location'], resp2.headers['Location'])
