import json
import requests
from website import settings

from osf.external.oopspam.exceptions import OOPSpamClientError


class OOPSpamClient(object):

    NAME = 'oopspam'
    API_PROTOCOL = 'https://'
    API_HOST = 'oopspam.p.rapidapi.com/v1/spamdetection'
    API_URL = f'{API_PROTOCOL}{API_HOST}'
    apikey = settings.OOPSPAM_APIKEY
    website = API_URL

    @property
    def _default_headers(self):
        return {
            'content-type': 'application/json',
            'x-rapidapi-key': self.apikey,
            'x-rapidapi-host': 'oopspam.p.rapidapi.com'
        }

    def check_content(self, user_ip, content, **kwargs):
        if not settings.OOPSPAM_ENABLED:
            return False, ''

        payload = {
            'checkForLength': False,
            'content': content
        }
        if settings.OOPSPAM_CHECK_IP:
            payload['senderIP'] = user_ip

        response = requests.request(
            'POST',
            self.website,
            data=json.dumps(payload),
            headers=self._default_headers
        )

        if response.status_code != requests.codes.ok:
            raise OOPSpamClientError(reason=response.text)

        resp_json = response.json()
        spam_score = resp_json['Score']

        #  OOPSpam returns a spam score out of 6. 3 or higher indicates spam
        return spam_score >= settings.OOPSPAM_SPAM_LEVEL, resp_json
