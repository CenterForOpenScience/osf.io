from datetime import timedelta
from rest_framework import status as http_status

from django.utils import timezone
from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import campaigns, views as auth_views, cas
from website.util import web_url_for
from osf_tests import factories
from tests.base import OsfTestCase
from tests.utils import mock_auth


def set_preprint_providers():
    """Populate `PreprintProvider` to test database for testing."""

    providers = {
        'osf': 'Open Science Framework',
        'socarxiv': 'SocArXiv',
        'engrxiv': 'EngrXiv',
        'psyarxiv': 'PsyArXiv',
    }

    for key, value in providers.items():
        provider = factories.PreprintProviderFactory()
        provider._id = key
        provider.name = value
        provider.save()


# tests for campaign initialization and update
class TestCampaignInitialization(OsfTestCase):

    def setUp(self):
        super(TestCampaignInitialization, self).setUp()
        set_preprint_providers()
        self.campaign_lists = [
            'prereg',
            'erpc',
            'institution',
            'osf-preprints',
            'socarxiv-preprints',
            'engrxiv-preprints',
            'psyarxiv-preprints',
            'osf-registries',
            'osf-registered-reports',
        ]
        self.refresh = timezone.now()
        campaigns.CAMPAIGNS = None  # force campaign refresh now that preprint providers are populated
        campaigns.CAMPAIGNS_LAST_REFRESHED = self.refresh

    def test_get_campaigns_init(self):
        campaign_dict = campaigns.get_campaigns()
        assert_equal(len(campaign_dict), len(self.campaign_lists))
        for campaign in campaign_dict:
            assert_in(campaign, self.campaign_lists)
        assert_not_equal(self.refresh, campaigns.CAMPAIGNS_LAST_REFRESHED)

    def test_get_campaigns_update_not_expired(self):
        campaigns.get_campaigns()
        self.refresh = campaigns.CAMPAIGNS_LAST_REFRESHED
        campaigns.get_campaigns()
        assert_equal(self.refresh, campaigns.CAMPAIGNS_LAST_REFRESHED)

    def test_get_campaigns_update_expired(self):
        campaigns.get_campaigns()
        self.refresh = timezone.now() - timedelta(minutes=5)
        campaigns.CAMPAIGNS_LAST_REFRESHED = self.refresh
        campaigns.get_campaigns()
        assert_not_equal(self.refresh, campaigns.CAMPAIGNS_LAST_REFRESHED)


# tests for campaign helper methods
class TestCampaignMethods(OsfTestCase):

    def setUp(self):
        super(TestCampaignMethods, self).setUp()
        set_preprint_providers()
        self.campaign_lists = [
            'prereg',
            'erpc',
            'institution',
            'osf-preprints',
            'socarxiv-preprints',
            'engrxiv-preprints',
            'psyarxiv-preprints',
        ]
        self.invalid_campaign = 'invalid_campaign'
        campaigns.CAMPAIGNS = None  # force campaign refresh now that preprint providers are populated

    def test_is_institution_login(self):
        for campaign in self.campaign_lists:
            institution = campaigns.is_institution_login(campaign)
            if campaign == 'institution':
                assert_true(institution)
            else:
                assert_false(institution)
        institution = campaigns.is_institution_login(self.invalid_campaign)
        assert_true(institution is None)

    def test_is_native_login(self):
        for campaign in self.campaign_lists:
            native = campaigns.is_native_login(campaign)
            if campaign == 'prereg' or campaign == 'erpc':
                assert_true(native)
            else:
                assert_false(native)
        native = campaigns.is_proxy_login(self.invalid_campaign)
        assert_true(native is None)

    def test_is_proxy_login(self):
        for campaign in self.campaign_lists:
            proxy = campaigns.is_proxy_login(campaign)
            if campaign.endswith('-preprints'):
                assert_true(proxy)
            else:
                assert_false(proxy)
        proxy = campaigns.is_proxy_login(self.invalid_campaign)
        assert_true(proxy is None)

    def test_system_tag_for_campaign(self):
        for campaign in self.campaign_lists:
            tag = campaigns.system_tag_for_campaign(campaign)
            assert_true(tag is not None)
        tag = campaigns.system_tag_for_campaign(self.invalid_campaign)
        assert_true(tag is None)

    def test_email_template_for_campaign(self):
        for campaign in self.campaign_lists:
            template = campaigns.email_template_for_campaign(campaign)
            if campaigns.is_institution_login(campaign):
                assert_true(template is None)
            else:
                assert_true(template is not None)
        template = campaigns.email_template_for_campaign(self.invalid_campaign)
        assert_true(template is None)

    def test_campaign_url_for(self):
        for campaign in self.campaign_lists:
            url = campaigns.campaign_url_for(campaign)
            assert_true(url is not None)
        url = campaigns.campaign_url_for(self.invalid_campaign)
        assert_true(url is None)

    def test_get_service_provider(self):
        for campaign in self.campaign_lists:
            provider = campaigns.get_service_provider(campaign)
            if campaigns.is_proxy_login(campaign):
                assert_true(provider is not None)
            else:
                assert_true(provider is None)
        provider = campaigns.get_service_provider(self.invalid_campaign)
        assert_true(provider is None)

    def test_campaign_for_user(self):
        user = factories.UserFactory()
        user.add_system_tag('osf_preprints')
        user.save()
        campaign = campaigns.campaign_for_user(user)
        assert_equal(campaign, 'osf-preprints')


# tests for prereg, erpc, which follow similar auth login/register logic
class TestCampaignsAuthViews(OsfTestCase):

    def setUp(self):
        super(TestCampaignsAuthViews, self).setUp()
        self.campaigns = {
            'prereg': {
                'title_register': 'Preregistration Challenge',
                'title_landing': 'Welcome to the Prereg Challenge!'
            },
            'erpc': {
                'title_register': 'Election Research Preacceptance Competition',
                'title_landing': 'The Election Research Preacceptance Competition is Now Closed'
            },
        }
        for key, value in self.campaigns.items():
            value.update({'url_login': web_url_for('auth_login', campaign=key)})
            value.update({'url_register': web_url_for('auth_register', campaign=key)})
            value.update({'url_landing': campaigns.campaign_url_for(key)})
        self.user = factories.AuthUserFactory()

    def test_campaign_register_view_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_register'], auth=self.user.auth)
            assert_equal(resp.status_code, http_status.HTTP_302_FOUND)
            assert_equal(value['url_landing'], resp.headers['Location'])

    def test_campaign_register_view_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_register'])
            assert_equal(resp.status_code, http_status.HTTP_200_OK)
            assert_in(value['title_register'], resp)

    def test_campaign_login_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_login'], auth=self.user.auth)
            assert_equal(resp.status_code, http_status.HTTP_302_FOUND)
            assert_in(value['url_landing'], resp.headers['Location'])

    def test_campaign_login_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_login'])
            assert_equal(resp.status_code, http_status.HTTP_302_FOUND)
            assert_in(value['url_register'], resp.headers['Location'])

    def test_campaign_landing_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_landing'], auth=self.user.auth)
            assert_equal(resp.status_code, http_status.HTTP_200_OK)

    def test_auth_prereg_landing_page_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_landing'])
            assert_equal(resp.status_code, http_status.HTTP_200_OK)


# tests for registration through campaigns
class TestRegistrationThroughCampaigns(OsfTestCase):

    def setUp(self):
        super(TestRegistrationThroughCampaigns, self).setUp()

    def test_confirm_email_get_with_campaign(self):
        for key, value in campaigns.CAMPAIGNS.items():
            user = factories.UnconfirmedUserFactory()
            user.add_system_tag(value.get('system_tag'))
            user.save()
            token = user.get_confirmation_token(user.username)
            kwargs = {
                'uid': user._id,
            }
            with self.app.app.test_request_context(), mock_auth(user):
                res = auth_views.confirm_email_get(token, **kwargs)
                assert_equal(res.status_code, http_status.HTTP_302_FOUND)
                assert_equal(res.location, campaigns.campaign_url_for(key))


# tests for institution
class TestCampaignsCASInstitutionLogin(OsfTestCase):

    def setUp(self):
        super(TestCampaignsCASInstitutionLogin, self).setUp()
        self.url_login = web_url_for('auth_login', campaign='institution')
        self.url_register = web_url_for('auth_register', campaign='institution')
        self.service_url = web_url_for('dashboard', _absolute=True)

    # go to CAS institution login page if not logged in
    def test_institution_not_logged_in(self):
        resp = self.app.get(self.url_login)
        assert_equal(resp.status_code, http_status.HTTP_302_FOUND)
        assert_in(cas.get_login_url(self.service_url, campaign='institution'), resp.headers['Location'])
        # register behave the same as login
        resp2 = self.app.get(self.url_register)
        assert_equal(resp.headers['Location'], resp2.headers['Location'])

    # go to target page (service url_ if logged in
    def test_institution_logged_in(self):
        resp = self.app.get(self.url_login)
        assert_equal(resp.status_code, http_status.HTTP_302_FOUND)
        assert_in(self.service_url, resp.headers['Location'])
        # register behave the same as login
        resp2 = self.app.get(self.url_register)
        assert_equal(resp.headers['Location'], resp2.headers['Location'])
