"""

"""

from bs4 import BeautifulSoup
import requests

from framework import fields

from website.addons.base import AddonNodeSettingsBase

API_URL = 'https://api.zotero.org/groups/{zid}/items'
params = {
    'order': 'dateAdded',
    'sort': 'desc',
    'limit': 5,
}


class AddonZoteroNodeSettings(AddonNodeSettingsBase):

    zotero_id = fields.StringField()

    def _fetch_references(self):

        url = API_URL.format(
            zid=self.zotero_id,
        )

        xml = requests.get(url, params=params)

        return xml.content

    def _summarize_references(self):

        xml = self._fetch_references()
        parsed = BeautifulSoup(xml)
        titles = parsed.select('entry title')
        if titles:
            return '''
                <ul>
                    {lis}
                </ul>
            '''.format(
                lis=''.join([
                    '<li>{}</li>'.format(title.string)
                    for title in titles
                ])
            )

    def to_json(self, user):
        return {
            'zotero_id': self.zotero_id,
        }
