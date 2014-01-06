"""

"""

from bs4 import BeautifulSoup

from website.addons.base import AddonSettingsBase

class AddonWikiSettings(AddonSettingsBase):

    def render_widget(self):
        wiki_page = self.node.get_wiki_page('home')
        if wiki_page and wiki_page.html:
            wiki_html = wiki_page.html
            if len(wiki_html) > 500:
                wiki_html = BeautifulSoup(wiki_html[:500] + '...', 'html.parser')
            else:
                wiki_html = BeautifulSoup(wiki_html)
            return u'''
                <div>{wiki}</div>
                <p><a href="{url}wiki/home/">Read more</a></p>
            '''.format(
                wiki=wiki_html,
                url=self.node.url,
            )
        return u'<p><em>No wiki content</em></p>'

    def render_tab(self):
        return {
            'href': '{0}wiki/'.format(self.node.url),
            'text': 'Wiki',
        }
