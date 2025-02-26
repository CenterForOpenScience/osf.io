from datetime import timedelta
from urllib.parse import quote_plus

from rest_framework import status as http_status

from django.utils import timezone

from framework.auth import campaigns, views as auth_views, cas
from website.util import web_url_for
from website.util.metrics import provider_source_tag
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
        super().setUp()
        set_preprint_providers()
        self.campaign_lists = [
            'erpc',
            'institution',
            'osf-preprints',
            'socarxiv-preprints',
            'engrxiv-preprints',
            'psyarxiv-preprints',
            'osf-registries',
            'osf-registered-reports',
            'agu_conference_2023',
            'agu_conference',
        ]
        self.refresh = timezone.now()
        campaigns.CAMPAIGNS = None  # force campaign refresh now that preprint providers are populated
        campaigns.CAMPAIGNS_LAST_REFRESHED = self.refresh

    def test_get_campaigns_init(self):
        campaign_dict = campaigns.get_campaigns()
        assert len(campaign_dict) == len(self.campaign_lists)
        for campaign in campaign_dict:
            assert campaign in self.campaign_lists
        assert self.refresh != campaigns.CAMPAIGNS_LAST_REFRESHED

    def test_get_campaigns_update_not_expired(self):
        campaigns.get_campaigns()
        self.refresh = campaigns.CAMPAIGNS_LAST_REFRESHED
        campaigns.get_campaigns()
        assert self.refresh == campaigns.CAMPAIGNS_LAST_REFRESHED

    def test_get_campaigns_update_expired(self):
        campaigns.get_campaigns()
        self.refresh = timezone.now() - timedelta(minutes=5)
        campaigns.CAMPAIGNS_LAST_REFRESHED = self.refresh
        campaigns.get_campaigns()
        assert self.refresh != campaigns.CAMPAIGNS_LAST_REFRESHED


# tests for campaign helper methods
class TestCampaignMethods(OsfTestCase):

    def setUp(self):
        super().setUp()
        set_preprint_providers()
        self.campaign_lists = [
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
                assert institution
            else:
                assert not institution
        institution = campaigns.is_institution_login(self.invalid_campaign)
        assert institution is None

    def test_is_native_login(self):
        for campaign in self.campaign_lists:
            native = campaigns.is_native_login(campaign)
            if campaign == 'erpc':
                assert native
            else:
                assert not native
        native = campaigns.is_proxy_login(self.invalid_campaign)
        assert native is None

    def test_is_proxy_login(self):
        for campaign in self.campaign_lists:
            proxy = campaigns.is_proxy_login(campaign)
            if campaign.endswith('-preprints'):
                assert proxy
            else:
                assert not proxy
        proxy = campaigns.is_proxy_login(self.invalid_campaign)
        assert proxy is None

    def test_system_tag_for_campaign(self):
        for campaign in self.campaign_lists:
            tag = campaigns.system_tag_for_campaign(campaign)
            assert tag is not None
        tag = campaigns.system_tag_for_campaign(self.invalid_campaign)
        assert tag is None

    def test_email_template_for_campaign(self):
        for campaign in self.campaign_lists:
            template = campaigns.email_template_for_campaign(campaign)
            if campaigns.is_institution_login(campaign):
                assert template is None
            else:
                assert template is not None
        template = campaigns.email_template_for_campaign(self.invalid_campaign)
        assert template is None

    def test_campaign_url_for(self):
        for campaign in self.campaign_lists:
            url = campaigns.campaign_url_for(campaign)
            assert url is not None
        url = campaigns.campaign_url_for(self.invalid_campaign)
        assert url is None

    def test_get_service_provider(self):
        for campaign in self.campaign_lists:
            provider = campaigns.get_service_provider(campaign)
            if campaigns.is_proxy_login(campaign):
                assert provider is not None
            else:
                assert provider is None
        provider = campaigns.get_service_provider(self.invalid_campaign)
        assert provider is None

    def test_campaign_for_user(self):
        user = factories.UserFactory()
        user.add_system_tag(provider_source_tag('osf', 'preprint'))
        user.save()
        campaign = campaigns.campaign_for_user(user)
        assert campaign == 'osf-preprints'


# tests for prereg, erpc, which follow similar auth login/register logic
class TestCampaignsAuthViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.campaigns = {
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
            assert resp.status_code == http_status.HTTP_302_FOUND
            assert value['url_landing'] == resp.headers['Location']

    def test_campaign_register_view_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_register'])
            assert resp.status_code == http_status.HTTP_200_OK
            assert value['title_register'] in resp.text

    def test_campaign_login_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_login'], auth=self.user.auth)
            assert resp.status_code == http_status.HTTP_302_FOUND
            assert value['url_landing'] in resp.headers['Location']

    def test_campaign_login_logged_out(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_login'])
            assert resp.status_code == http_status.HTTP_302_FOUND
            assert value['url_register'] in resp.headers['Location']

    def test_campaign_landing_logged_in(self):
        for key, value in self.campaigns.items():
            resp = self.app.get(value['url_landing'], auth=self.user.auth)
            assert resp.status_code == http_status.HTTP_200_OK


# tests for registration through campaigns
class TestRegistrationThroughCampaigns(OsfTestCase):

    def setUp(self):
        super().setUp()
        campaigns.get_campaigns()  # Set up global CAMPAIGNS

    def test_confirm_email_get_with_campaign(self):
        for key, value in campaigns.CAMPAIGNS.items():
            user = factories.UnconfirmedUserFactory()
            user.add_system_tag(value.get('system_tag'))
            user.save()
            token = user.get_confirmation_token(user.username)
            kwargs = {
                'uid': user._id,
            }
            with self.app.application.test_request_context(), mock_auth(user):
                res = auth_views.confirm_email_get(token, **kwargs)
                assert res.status_code == http_status.HTTP_302_FOUND
                assert res.location == campaigns.campaign_url_for(key)


# tests for institution
class TestCampaignsCASInstitutionLogin(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.url_login = web_url_for('auth_login', campaign='institution')
        self.url_register = web_url_for('auth_register', campaign='institution')
        self.service_url = web_url_for('dashboard', _absolute=True)

    # go to CAS institution login page if not logged in
    def test_institution_not_logged_in(self):
        resp = self.app.get(self.url_login)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_login_url(self.service_url, campaign='institution') in resp.headers['Location']
        # register behave the same as login
        resp2 = self.app.get(self.url_register)
        assert resp.headers['Location'] == resp2.headers['Location']

    # go to target page (service url_ if logged in
    def test_institution_logged_in(self):
        # TODO: check in qa url encoding
        resp = self.app.get(self.url_login)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert quote_plus(self.service_url) in resp.headers['Location']
        # register behave the same as login
        resp2 = self.app.get(self.url_register)
        assert resp.headers['Location'] == resp2.headers['Location']
