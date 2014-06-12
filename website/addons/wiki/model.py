"""

"""

import datetime
import markdown
from markdown.extensions import wikilinks

from framework.forms.utils import sanitize
from framework import fields
from framework import GuidStoredObject

from website import settings
from website.addons.base import AddonNodeSettingsBase


class AddonWikiNodeSettings(AddonNodeSettingsBase):

    def to_json(self, user):
        return {}


class NodeWikiPage(GuidStoredObject):

    redirect_mode = 'redirect'

    _id = fields.StringField(primary=True)

    page_name = fields.StringField()
    version = fields.IntegerField()
    date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    is_current = fields.BooleanField()
    content = fields.StringField()

    user = fields.ForeignField('user')
    node = fields.ForeignField('node')

    @property
    def deep_url(self):
        return '{}wiki/{}/'.format(self.node.deep_url, self.page_name)

    @property
    def url(self):
        return '{}wiki/{}/'.format(self.node.url, self.page_name)

    @property
    def html(self):
        """The cleaned HTML of the page"""

        html_output = markdown.markdown(
            self.content,
            extensions=[
                wikilinks.WikiLinkExtension(
                    configs=[('base_url', ''), ('end_url', '')]
                )
            ]
        )

        return sanitize(html_output, **settings.WIKI_WHITELIST)

    @property
    def raw_text(self):
        """ The raw text of the page, suitable for using in a test search"""

        return sanitize(self.html, tags=[], strip=True)

    def save(self, *args, **kwargs):
        rv = super(NodeWikiPage, self).save(*args, **kwargs)
        if self.node:
            self.node.update_search() 
        return rv
