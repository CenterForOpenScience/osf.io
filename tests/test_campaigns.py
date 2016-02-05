import httplib as http

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import campaigns, views as auth_views

from website.util import web_url_for
from website.project.model import ensure_schemas

from tests import factories
from tests.base import OsfTestCase
from tests.utils import mock_auth


class TestCampaigns(OsfTestCase):

    def test_auth_login_with_campaign_logged_out(self):
        url = web_url_for('auth_login', campaign='prereg')
        with self.app.app.test_request_context(url):
            data, status_code = auth_views.auth_login()
            assert_equal(status_code, http.OK)

            assert_equal(data['campaign'], 'prereg')
            assert_in('prereg', data['login_url'])

    def test_auth_login_with_campaign_logged_in(self):
        ensure_schemas()
        url = web_url_for('auth_login', campaign='prereg')
        user = factories.AuthUserFactory()
        with self.app.app.test_request_context(url), mock_auth(user):
            res = auth_views.auth_login()
            assert_equal(res.status_code, http.FOUND)
            assert_equal(res.location, campaigns.CAMPAIGNS['prereg']['redirect_url']())

    def test_confirm_email_get_with_campaign(self):
        user = factories.UnconfirmedUserFactory()
        user.system_tags.append(campaigns.CAMPAIGNS['prereg']['system_tag'])
        user.save()
        token = user.get_confirmation_token(user.username)
        kwargs = {
            'uid': user._id,
        }
        with self.app.app.test_request_context(), mock_auth(user):
            res = auth_views.confirm_email_get(token, **kwargs)
            assert_equal(res.status_code, http.FOUND)
            assert_equal(res.location, campaigns.CAMPAIGNS['prereg']['redirect_url']())
