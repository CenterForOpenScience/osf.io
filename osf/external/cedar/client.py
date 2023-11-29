import requests

from urllib.parse import quote_plus

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
        # TODO: add error handling
        r = requests.get(url, headers=self.headers)
        resources = r.json()['resources']
        return [item['@id'] for item in resources]

    def retrieve_template_by_id(self, id):
        url = f'{self.host}templates/{quote_plus(id)}'
        # TODO: add error handling
        r = requests.get(url, headers=self.headers)
        return r.json()
