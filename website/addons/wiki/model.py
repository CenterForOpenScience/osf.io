"""

"""

import datetime
import functools

from bleach import linkify
from bleach.callbacks import nofollow

import markdown
from markdown.extensions import codehilite, fenced_code, wikilinks

from modularodm import fields
from modularodm.exceptions import ValidationValueError

from framework.forms.utils import sanitize
from framework.guid.model import GuidStoredObject

from website import settings
from website.addons.base import AddonNodeSettingsBase

from .exceptions import (
    NameEmptyError,
    NameMaximumLengthError,
)


class AddonWikiNodeSettings(AddonNodeSettingsBase):

    def to_json(self, user):
        return {}


def build_wiki_url(node, label, base, end):
    return node.web_url_for('project_wiki_page', wname=label)

def validate_page_name(value):
    value = value or ''
    value = value.strip()

    if not value:
        raise NameEmptyError('Page name cannot be blank.')
    if len(value) > 100:
        raise NameMaximumLengthError('Page name cannot be greater than 100 characters.')
    return True

class NodeWikiPage(GuidStoredObject):

    redirect_mode = 'redirect'

    _id = fields.StringField(primary=True)

    page_name = fields.StringField(validate=validate_page_name)
    version = fields.IntegerField()
    date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    is_current = fields.BooleanField()
    content = fields.StringField(default='')

    user = fields.ForeignField('user')
    node = fields.ForeignField('node')

    @property
    def deep_url(self):
        return '{}wiki/{}/'.format(self.node.deep_url, self.page_name)

    @property
    def url(self):
        return '{}wiki/{}/'.format(self.node.url, self.page_name)

    def html(self, node):
        """The cleaned HTML of the page"""

        html_output = markdown.markdown(
            self.content,
            extensions=[
                wikilinks.WikiLinkExtension(
                    configs=[
                        ('base_url', ''),
                        ('end_url', ''),
                        ('build_url', functools.partial(build_wiki_url, node))
                    ]
                ),
                fenced_code.FencedCodeExtension(),
                codehilite.CodeHiliteExtension(
                    [('css_class', 'highlight')]
                )
            ]
        )

        # linkify gets called after santize, because we're adding rel="nofollow"
        #   to <a> elements - but don't want to allow them for other elements.
        return linkify(
            sanitize(html_output, **settings.WIKI_WHITELIST),
            [nofollow, ],
        )

    def raw_text(self, node):
        """ The raw text of the page, suitable for using in a test search"""

        return sanitize(self.html(node), tags=[], strip=True)

    def save(self, *args, **kwargs):
        rv = super(NodeWikiPage, self).save(*args, **kwargs)
        if self.node:
            self.node.update_search()
        return rv

    def rename(self, new_name, save=True):
        self.page_name = new_name
        if save:
            self.save()

    def to_json(self):
        return {}
