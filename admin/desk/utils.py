"""
Modified from https://gist.github.com/pamelafox/5855372
"""
from django.conf import settings

import requests
import json
from requests_oauthlib import OAuth1Session


class DeskError(Exception):
    pass


class DeskClient(object):
    """ Initialize the client with the given sitename, username,
    and password. The suggested way to do this in the Desk docs for
    a single person is to use Basic Auth.
    """
    BASE_URL = 'desk.com/api/v2'
    SITE_NAME = 'openscience'

    def __init__(self, user):
        self.oauth = OAuth1Session(
            settings.DESK_KEY,
            client_secret=settings.DESK_KEY_SECRET,
            resource_owner_key=user.desk_token,
            resource_owner_secret=user.desk_token_secret
        )

    def build_url(self, service):
        """ Constructs the URL for a given service."""
        return 'https://%s.%s/%s' % (self.SITE_NAME, DeskClient.BASE_URL, service)

    def call_get(self, service, params=None):
        """ Calls a GET API for the given service name and URL parameters."""
        url = self.build_url(service)
        r = self.oauth.get(url, params=params)
        if r.status_code != requests.codes.ok:
            raise DeskError('{}: {}'.format(r.status_code, r.reason))
        return r.json()  # json.loads(r.content)

    def call_post(self, service, data=None):
        """ Calls a POST API for the given service name and POST data."""
        url = self.build_url(service)
        r = self.oauth.post(url, data=json.dumps(data))
        if r.status_code >= 400:
            raise DeskError(str(r.status_code))
        return json.loads(r.content)

    def find_customer(self, params):
        """ Finds a customer based on the given parameters.
            Documentation: http://dev.desk.com/API/customers/#search
            Example URL: https://yoursite.desk.com/api/v2/customers/search?email=andrew@example.com
        """
        customer_data = {}
        try:
            customer_json = self.call_get('customers/search', params)
            if customer_json['total_entries'] > 0:
                customer = customer_json['_embedded']['entries'][0]
                customer_data = {
                    'id': customer['id'],
                    'name': '{} {}'.format(
                        customer['first_name'], customer['last_name']),
                    'emails': customer['emails'],
                    'background': customer['background'],
                    'company': customer['company'],
                    'link': customer['_links']['self']
                }
        except DeskError:
            raise
        return customer_data

    def cases(self, params):
        case_list = [None]
        params.update({
            'sort_field': 'created_at',
            'sort_direction': 'desc'
        })
        try:
            case_list = self.call_get('cases/search', params)
        except DeskError:
            raise
        return case_list[u'_embedded'][u'entries']
