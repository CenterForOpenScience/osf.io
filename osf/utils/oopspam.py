import requests
import json

from website import settings

class OOPSpamClientError(Exception):

    def __init__(self, reason):
        super(OOPSpamClientError, self).__init__(reason)
        self.reason = reason

class OOPSpamClient(object):

    API_PROTOCOL = 'https://'
    API_HOST = 'oopspam.p.rapidapi.com/v1/spamdetection'
    API_URL = f'{API_PROTOCOL}{API_HOST}'

    def __init__(self, apikey=None, website=None):
        self.apikey = apikey or settings.OOPSPAM_APIKEY
        self.website = website or self.API_URL

    @property
    def _default_headers(self):
        return {
            'content-type': 'application/json',
            'x-rapidapi-key': self.apikey,
            'x-rapidapi-host': 'oopspam.p.rapidapi.com'
        }

    def check_content(self, user_ip, content):
        if not self.apikey:
            return False, ''
        payload = {}
        payload['checkForLength'] = False
        payload['content'] = content
        if settings.OOPSPAM_CHECK_IP:
            payload['senderIP'] = user_ip

        headers = self._default_headers

        response = requests.request('POST', self.website, data=json.dumps(payload), headers=headers)

        if response.status_code != requests.codes.ok:
            raise OOPSpamClientError(reason=response.text)

        resp_json = response.json()
        spam_score = resp_json['Score']

        #  OOPSpam returns a spam score out of 6. 3 or higher indicates spam
        return spam_score >= settings.OOPSPAM_SPAM_LEVEL, resp_json
