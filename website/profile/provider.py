# import httplib as http

# from framework.auth import Auth
# from framework.exceptions import HTTPError, PermissionsError
from website.profile import serializer
# from website.oauth.models import ExternalAccount
from website.oauth.models import OAUTH1
from website.oauth.models import ExternalProvider
from website import settings


class TwitterProvider(ExternalProvider):
    name = 'Twitter'
    short_name = 'twitter'
    provider_name = 'twitter'

    serializer = serializer.TwitterSerializer

    client_id = settings.TWITTER_CLIENT_ID
    client_secret = settings.TWITTER_CLIENT_SECRET

    auth_url_base = 'https://api.twitter.com/oauth/authorize'
    callback_url = 'https://api.twitter.com/oauth/access_token'
    request_token_url = 'https://api.twitter.com/oauth/request_token'
    default_scopes = ['all']

    # Default to OAuth v2.0.
    _oauth_version = OAUTH1

    def handle_callback(self, response):
        return {
            'provider_id': response['user_id'],
            'display_name': response['screen_name'],
            'profile_url': 'https://twitter.com/' + response['screen_name'],
        }
