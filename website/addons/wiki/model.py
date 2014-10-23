"""

"""

import datetime
import functools
import uuid

from bleach import linkify
from bleach.callbacks import nofollow
import markdown
from markdown.extensions import codehilite, fenced_code, wikilinks
from modularodm import fields

from framework.forms.utils import sanitize
from framework.guid.model import GuidStoredObject
from framework.mongo.utils import to_mongo_key
from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.wiki.utils import (docs_uuid, ops_uuid, share_db,
                                       generate_share_uuid)

from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
)


class AddonWikiNodeSettings(AddonNodeSettingsBase):

    def to_json(self, user):
        return {}


def build_wiki_url(node, label, base, end):
    return node.web_url_for('project_wiki_page', wname=label)


def validate_page_name(value):
    value = (value or '').strip()

    if not value:
        raise NameEmptyError('Page name cannot be blank.')
    if value.find('/') != -1:
        raise NameInvalidError('Page name cannot contain forward slashes.')
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
    share_uuid = fields.StringField()

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

    # TODO: Improve handling of page names in migration and deletion

    def delete_share_doc(self, node, save=True):
        """Deletes share document and removes namespace from model."""

        db = share_db()

        db[ops_uuid(node, self.share_uuid)].drop()
        db['docs'].remove({'_id': docs_uuid(node, self.share_uuid)})

        self.share_uuid = None

        wiki_key = to_mongo_key(self.page_name)
        del node.wiki_sharejs_uuids[wiki_key]
        node.save()

        if save:
            self.save()

    """ TODO: Migrate when page is open, followed by edits to the old doc,
        leads to a sharejs document with no pointer. This is both a security
        risk and a memory leak."""
    def migrate_uuid(self, node, save=True):
        """Migrates uuid to new namespace."""

        db = share_db()

        old_uuid = self.share_uuid
        self.share_uuid = generate_share_uuid(node, self.page_name)

        ops_collection = db[ops_uuid(node, old_uuid)]
        if ops_collection.find_one():  # Collection exists
            ops_collection.rename(ops_uuid(node, self.share_uuid))

            new_doc = db['docs'].find_one({'_id': docs_uuid(node, old_uuid)})
            if new_doc:
                new_doc['_id'] = docs_uuid(node, self.share_uuid)
                db['docs'].insert(new_doc)
                db['docs'].remove({'_id': docs_uuid(node, old_uuid)})

        if save:
            self.save()

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
