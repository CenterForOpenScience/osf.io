"""

"""

import datetime
import functools
import logging

from bleach import linkify
from bleach.callbacks import nofollow
import markdown
from markdown.extensions import codehilite, fenced_code, wikilinks
from modularodm import fields
import requests

from framework.forms.utils import sanitize
from framework.guid.model import GuidStoredObject
from framework.mongo.utils import to_mongo_key
from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.wiki.utils import to_mongo_uuid, share_db, generate_share_uuid

from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
)


logger = logging.getLogger(__name__)


class AddonWikiNodeSettings(AddonNodeSettingsBase):

    def after_remove_contributor(self, node, removed):

        # Migrate every page on the node
        for wiki_name in node.wiki_pages_current:
            wiki_page = node.get_wiki_page(wiki_name)
            wiki_page.migrate_uuid(node)

        # TODO: Does this affect forks?

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


def render_content(content, node):
    html_output = markdown.markdown(
        content,
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
    sanitized_content = sanitize(html_output, **settings.WIKI_WHITELIST)
    return sanitized_content


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
        sanitized_content = render_content(self.content, node=node)
        try:
            return linkify(
                sanitized_content,
                [nofollow, ],
            )
        except TypeError:
            logger.warning('Returning unlinkified content.')
            return sanitized_content

    def raw_text(self, node):
        """ The raw text of the page, suitable for using in a test search"""

        return sanitize(self.html(node), tags=[], strip=True)

    def delete_share_doc(self, node, save=True):
        """Deletes share document and removes namespace from model."""

        db = share_db()
        mongo_uuid = to_mongo_uuid(node, self.share_uuid)

        # db[ops_uuid(node, self.share_uuid)].drop()
        db['docs'].remove({'_id': mongo_uuid})
        db['docs_ops'].remove({'name': mongo_uuid})

        self.share_uuid = None

        wiki_key = to_mongo_key(self.page_name)
        del node.wiki_sharejs_uuids[wiki_key]
        node.save()

        if save:
            self.save()

    def migrate_uuid(self, node, save=True):
        """Migrates uuid to new namespace."""

        db = share_db()
        old_mongo_uuid = to_mongo_uuid(node, self.share_uuid)

        lock_url = 'http://{host}:{port}/{action}/{id}'.format(
            host=settings.SHAREJS_HOST,
            port=settings.SHAREJS_PORT,
            action='lock',
            id=old_mongo_uuid
        )
        requests.post(lock_url)

        self.share_uuid = generate_share_uuid(node, self.page_name)
        new_mongo_uuid = to_mongo_uuid(node, self.share_uuid)

        doc_item = db['docs'].find_one({'_id': old_mongo_uuid})
        if doc_item:
            doc_item['_id'] = new_mongo_uuid
            db['docs'].insert(doc_item)
            db['docs'].remove({'_id': old_mongo_uuid})

        ops_items = [item for item in db['docs_ops'].find({'name': old_mongo_uuid})]
        if ops_items:
            for item in ops_items:
                item['_id'] = item['_id'].replace(old_mongo_uuid, new_mongo_uuid)
                item['name'] = new_mongo_uuid
            db['docs_ops'].insert(ops_items)
            db['docs_ops'].remove({'name': old_mongo_uuid})

        unlock_url = 'http://{host}:{port}/{action}/{id}'.format(
            host=settings.SHAREJS_HOST,
            port=settings.SHAREJS_PORT,
            action='unlock',
            id=old_mongo_uuid
        )
        requests.post(unlock_url)

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
