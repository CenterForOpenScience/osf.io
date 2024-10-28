import json
import requests
from website import settings

from osf.external.oopspam.exceptions import OOPSpamClientError


class OOPSpamClient:

    def __init__(self, apikey=None, website=None):
        self.apikey = apikey or settings.OOPSPAM_APIKEY
        self.website = website or self.API_URL

    NAME = 'oopspam'
    API_PROTOCOL = 'https://'
    API_HOST = 'oopspam.p.rapidapi.com/v1/spamdetection'
    API_URL = f'{API_PROTOCOL}{API_HOST}'
    apikey = settings.OOPSPAM_APIKEY
    website = API_URL

    def check_content(self, user_ip, content, **kwargs):

        payload = {
            'checkForLength': False,
            'content': content
        }
        if settings.OOPSPAM_CHECK_IP:
            payload['senderIP'] = user_ip

        response = requests.post(
            self.website,
            data=json.dumps(payload),
            headers={
                'content-type': 'application/json',
                'x-rapidapi-key': self.apikey,
                'x-rapidapi-host': 'oopspam.p.rapidapi.com'
            }
        )

        if response.status_code != requests.codes.ok:
            raise OOPSpamClientError(reason=response.text)

        resp_json = response.json()
        spam_score = resp_json['Score']

        #  OOPSpam returns a spam score out of 6. 3 or higher indicates spam
        return spam_score >= settings.OOPSPAM_SPAM_LEVEL, resp_json

    def get_flagged_count(self, start_date, end_date):
        from osf.models import NodeLog

        flagged_count = NodeLog.objects.filter(
            action=NodeLog.FLAG_SPAM,
            created__gt=start_date,
            created__lt=end_date,
            node__spam_data__who_flagged__in=['oopspam', 'both']
        ).count()

        return flagged_count

    def get_hammed_count(self, start_date, end_date):
        from osf.models import NodeLog

        hammed_count = NodeLog.objects.filter(
            action=NodeLog.CONFIRM_HAM,
            created__gt=start_date,
            created__lt=end_date,
            node__spam_data__who_flagged__in=['oopspam', 'both']
        ).count()

        return hammed_count
