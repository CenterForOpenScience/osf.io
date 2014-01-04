"""

"""

from bs4 import BeautifulSoup
import requests
import json

from framework import fields

from website.addons.base import AddonSettingsBase

API_URL = 'https://api.zotero.org/groups/{zid}/items'
params = {
    'order': 'dateAdded',
    'sort': 'desc',
    'limit': 5,
}

# TODO: Use content=bibtex

class AddonZoteroSettings(AddonSettingsBase):

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

    def render_widget(self):
        if self.zotero_id:
            return self._summarize_references()

    def render_tab(self):
        return {
            'href': '{0}zotero/'.format(self.node.url),
            'text': 'Zotero',
        }

    def render_page(self):
        if self.zotero_id:
            return '''
                <h3>Zotero Page</h3>
                <div>{xml}</div>
            '''.format(
                xml=self._fetch_references()
            )
        return '''
            <div>
                Zotero page not configured:
                Configure this addon on the <a href="/{nid}/settings/">settings</a> page,
                or click <a class="widget-disable" href="{url}settings/zotero/disable/">here</a> to disable it.
            </div>
        '''.format(
            nid=self.node._primary_key,
            url=self.node.api_url,
        )

    def meta_json(self):
        return json.dumps({
            'zotero_id': self.zotero_id,
        })
