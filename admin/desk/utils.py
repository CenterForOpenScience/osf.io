"""
Modified from https://gist.github.com/pamelafox/5855372
"""

import requests
import json
from requests_oauthlib import OAuth1Session

from django.conf import settings


class DeskError(Exception):
    pass


class DeskClient(object):
    """ Initialize the client with the given sitename, username,
    and password. The suggested way to do this in the Desk docs for
    a single person is to use Basic Auth.
    """
    BASE_URL = 'desk.com/api/v2'
    SITE_NAME = 'openscience'

    def __init__(self):
        self.oauth = OAuth1Session(
            settings.DESK_KEY,
            client_secret=settings.DESK_KEY_SECRET,
            resource_owner_key=settings.DESK_TOKEN,
            resource_owner_secret=settings.DESK_TOKEN_SECRET
        )

    def build_url(self, service):
        """ Constructs the URL for a given service."""
        return 'https://%s.%s/%s' % (self.SITE_NAME, DeskClient.BASE_URL, service)

    def call_get(self, service, params=None):
        """ Calls a GET API for the given service name and URL parameters."""
        url = self.build_url(service)
        r = self.oauth.get(url, params=params)
        if r.status_code != requests.codes.ok:
            raise DeskError(str(r.status_code))
        return json.loads(r.content)

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
            pass
        return customer_data

    def create_customer(self, data):
        """ Creates a customer based on the given data.
            Documentation: http://dev.desk.com/API/customers/#create
            Example URL: https://yoursite.desk.com/api/v2/customers
            Example data:
            {
              "first_name": "Johnny",
              "emails": [
                {
                  "type": "work",
                  "value": "johnny@acme.com"
                },
                {
                  "type": "other",
                  "value": "johnny@other.com"
                }
              ],
              "custom_fields": {
                "level": "super"
              }
            }
        """
        customer_link = None
        try:
            customer_json = self.call_post('customers', data)
            if not customer_json.get('errors'):
                customer_link = customer_json['_links']['self']['href']
        except DeskError:
            pass
        return customer_link

    def create_case(self, data):
        """ Creates a case based on the given data.
        Documentation: http://dev.desk.com/API/cases/#create
        Example URL: https://yoursite.desk.com/api/v2/cases
        Example data:
        {
          "type": "email",
          "subject": "Creating a case via the API",
          "priority": 4,
          "status": "open",
          "labels": [
            "Spam",
            "Ignore"
          ],
          "language": "fr",
          "message": {
            "direction": "in",
            "status": "received",
            "to": "someone@desk.com",
            "from": "someone-else@desk.com",
            "cc": "alpha@desk.com",
            "bcc": "beta@desk.com",
            "subject": "Creating a case via the API",
            "body": "Please assist me with this case",
            "created_at": "2012-05-02T21:38:48Z"
        }
        """
        case_link = None
        try:
            case_json = self.call_post('cases', data)
            if not case_json.get('errors'):
                case_link = case_json['_links']['self']['href']
        except DeskError:
            pass
        return case_link

    # def customer_cases(self, email):
    #     params = {'email': email}
    #     customer = self.find_customer(params)

    def cases(self, params):
        case_list = [None]
        params.update({
            'sort_field': 'created_at',
            'sort_direction': 'desc'
        })
        try:
            case_list = self.call_get('cases/search', params)
        except DeskError:
            pass
        return case_list[u'_embedded'][u'entries']

    def create_find_customer_by_email(self, email, full_name=None):
        """ A convenience function for finding or creating a customer, given an email.
            It tries to create the customer first, and if it gets a validation error
            about the customer already existing, it finds the customer.
            This optimizes for the case that new customers are more common
            than existing customers.
            It also takes care of turning a full name into separate first and last name fields.
        """
        first_name = email.split('@')[0]
        last_name = ''
        if full_name and full_name.find(' ') > -1:
            first_name = full_name.split(' ')[0]
            last_name = full_name.split(' ')[1:]
        elif full_name:
            first_name = full_name
        customer_link = self.create_customer({
            'emails': [{'type': 'home', 'value': email}],
            'first_name': first_name,
            'last_name': last_name})
        if not customer_link:
            customer_link = self.find_customer({'email': email})
        return customer_link

    def get_link_for_case(self, case_api_link):
        """ A convenience function for turning the link returned back by the case API
            into a web link that Desk agents can view."""
        case_number = case_api_link.split('/')[-1]
        return 'https://%s.desk.com/agent/case/%s' % (self.SITE_NAME, case_number)
