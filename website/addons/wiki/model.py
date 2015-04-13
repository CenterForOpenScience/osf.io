# -*- coding: utf-8 -*-

from datetime import datetime
import functools
import logging
import pytz
from furl import furl

from bleach import linkify
from bleach.callbacks import nofollow

import markdown
from markdown.extensions import codehilite, fenced_code, wikilinks
from modularodm import fields

from framework.forms.utils import sanitize
from framework.guid.model import GuidStoredObject

from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.wiki import utils as wiki_utils
from website.addons.wiki.settings import WIKI_CHANGE_DATE
from website.project.model import write_permissions_revoked, wiki_deleted, wiki_changed, wiki_renamed
from website.notifications.emails import notify

from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
)


logger = logging.getLogger(__name__)


class AddonWikiNodeSettings(AddonNodeSettingsBase):

    def after_register(self, node, registration, user, save=True):
        """Copy wiki settings to registrations."""
        clone = self.clone()
        clone.owner = registration
        if save:
            clone.save()
        return clone, None

    def to_json(self, user):
        return {}


@write_permissions_revoked.connect
def subscribe_on_write_permissions_revoked(node):
    # Migrate every page on the node
    for wiki_name in node.wiki_private_uuids:
        wiki_utils.migrate_uuid(node, wiki_name)


def wiki_updates(func):
    def func_wrapper(name, node, user, **kwargs):
        context = func(name, node, **kwargs)
        w_url = furl(node.absolute_url)
        try:
            w_url.path = context.pop('path')
        except KeyError:
            print "Please return path."
        w_url.add(context.pop('add', dict()))
        context['gravatar_url'] = user.gravatar_url
        context['url'] = w_url
        # timestamp set for testing purposes, can be passed in.
        if 'timestamp' in kwargs:
            timestamp = kwargs.get('timestamp')
        else:
            timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
        notify(
            uid=node._id,
            event="wiki_updated",
            user=user,
            node=node,
            timestamp=timestamp,
            **context
        )
    return func_wrapper


@wiki_deleted.connect
@wiki_updates
def subscribe_wiki_deleted(name, node, **kwargs):
    message = u'deleted <strong>"{}"</strong>.'.format(name)
    path = build_wiki_url(node, 'home')  # the wiki home
    return dict(path=path, message=message)


@wiki_changed.connect
@wiki_updates
def subscribe_wiki_changed(name, node, version=-1, **kwargs):
    path = build_wiki_url(node, name)
    add = dict()
    message = "None"
    if version == 1:
        message = u'added <strong>"{}"</strong>.'.format(name)
    elif version != 1:
        # Sends link with compare
        add = {'view': str(version), 'compare': str(version - 1)}
        message = u'updated <strong>"{}"</strong>; it is now version {}.' \
            .format(name, version)
    return dict(path=path, add=add, message=message)


@wiki_renamed.connect
@wiki_updates
def subscribe_wiki_renamed(name, node, new_name="wiki-error", **kwargs):
    message = u'renamed <strong>"{}"</strong> to <strong>"{}"</strong>' \
        .format(name, new_name)
    path = build_wiki_url(node, new_name)  # new wiki link
    return dict(path=path, message=message)


def build_wiki_url(node, label, base=None, end=None):
    return node.web_url_for('project_wiki_view', wname=label)


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

    _id = fields.StringField(primary=True)

    page_name = fields.StringField(validate=validate_page_name)
    version = fields.IntegerField()
    date = fields.DateTimeField(auto_now_add=datetime.utcnow)
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

    @property
    def rendered_before_update(self):
        return self.date < WIKI_CHANGE_DATE

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

    def get_draft(self, node):
        """
        Return most recently edited version of wiki, whether that is the
        last saved version or the most recent sharejs draft.
        """

        db = wiki_utils.share_db()
        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, self.page_name)

        doc_item = db['docs'].find_one({'_id': sharejs_uuid})
        if doc_item:
            sharejs_version = doc_item['_v']
            sharejs_timestamp = doc_item['_m']['mtime']
            sharejs_timestamp /= 1000   # Convert to appropriate units
            sharejs_date = datetime.utcfromtimestamp(sharejs_timestamp)

            if sharejs_version > 1 and sharejs_date > self.date:
                return doc_item['_data']

        return self.content

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
