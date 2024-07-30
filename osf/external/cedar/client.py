import requests
from requests.exceptions import JSONDecodeError, RequestException

from urllib.parse import quote_plus

from osf.external.cedar.exceptions import CedarClientRequestError, CedarClientResponseError
from website import settings


class CedarClient:

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
            raise CedarClientRequestError(
                reason=f'Fail to complete Cedar API request: home_folder_id={self.home_folder_id}'
            )
        try:
            resources = r.json()['resources']
        except JSONDecodeError:
            raise CedarClientResponseError(
                reason=f'Fail to parse Cedar API response: home_folder_id={self.home_folder_id}'
            )
        return [item['@id'] for item in resources]

    def retrieve_template_by_id(self, template_id):
        url = f'{self.host}templates/{quote_plus(template_id)}'
        try:
            r = requests.get(url, headers=self.headers)
            r.raise_for_status()
        except RequestException:
            raise CedarClientRequestError(reason=f'Fail to complete Cedar API request: template_id={template_id}')
        try:
            return r.json()
        except JSONDecodeError:
            raise CedarClientResponseError(reason=f'Fail to parse Cedar API response template_id={template_id}')
