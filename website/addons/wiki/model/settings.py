"""

"""

from bson import ObjectId
from bs4 import BeautifulSoup

from framework import fields
from website.addons.base import AddonSettingsBase

class AddonWikiSettings(AddonSettingsBase):

    url = fields.StringField()

    def render_widget(self):
        wiki_page = self.node.get_wiki_page('home')
        if wiki_page and wiki_page.html:
            wiki_html = wiki_page.html
            #if len(wiki_html) > 500:
            #    wiki_html = BeautifulSoup(wiki_html[:500] + '...', 'html.parser')
            #else:
            #    wiki_html = BeautifulSoup(wiki_html)
            wiki_html = BeautifulSoup(wiki_html)
            return '''
                <div>{wiki}</div>
                <p><a href="{url}wiki/home/">Read more</a></p>
            '''.format(
                wiki=wiki_html,
                url=self.node.url,
            )
        return '<p><em>No wiki content</em></p>'

    def render_tab(self):
        return '''
            <a href="{url}wiki/">Wiki</a>
        '''.format(
            url=self.node.url,
        )
