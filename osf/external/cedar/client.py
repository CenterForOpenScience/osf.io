import requests
from requests.exceptions import JSONDecodeError, RequestException

from urllib.parse import quote_plus

from osf.external.cedar.exceptions import CedarClientRequestError, CedarClientResponseError
from website import settings


class CedarClient(object):

    host = settings.CEDAR_API_HOST
    api_key = settings.CEDAR_API_KEY
    home_folder_id = quote_plus(settings.CEDAR_HOME_FOLDER_ID)
    headers = {
        'Authorization': f'apiKey {api_key}',
    }

    def retrieve_all_template_ids(self):
        url = f'{self.host}folders/{self.home_folder_id}/contents/?resource_types=template'
        try:
            r = requests.get(url, headers=self.headers)
            r.raise_for_status()
        except RequestException:
            raise CedarClientRequestError
        try:
            resources = r.json()['resources']
        except JSONDecodeError:
            raise CedarClientResponseError
        return [item['@id'] for item in resources]

    def retrieve_template_by_id(self, id):
        url = f'{self.host}templates/{quote_plus(id)}'
        try:
            r = requests.get(url, headers=self.headers)
            r.raise_for_status()
        except RequestException:
            raise CedarClientRequestError
        try:
            return r.json()
        except JSONDecodeError:
            raise CedarClientResponseError
