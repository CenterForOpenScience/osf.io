from website.oauth.models import ExternalProvider
# from website.util import web_url_for
from website import settings

class Twitter(ExternalProvider):
    name = 'Twitter'
    short_name = 'twitter'

    client_id = settings.TWITTER_CLIENT_ID
    client_secret = settings.TWITTER_CLIENT_SECRET

    auth_url_base = 'https://api.twitter.com/oauth/authorize'
    callback_url = 'https://api.twitter.com/oauth2/token'
    default_scopes = ['all']

    # _client = None

    def handle_callback(self, response):
        i  = 0
        # client = self._get_client(response)
        #
        # # make a second request for the Mendeley user's ID and name
        # profile = client.profiles.me
        #
        # return {
        #     'provider_id': profile.id,
        #     'display_name': profile.display_name,
        #     'profile_url': profile.link,
        # }
