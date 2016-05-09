# -*- coding: utf-8 -*-

import datetime
import functools
import logging
import urllib

from bleach import linkify
from bleach.callbacks import nofollow
from website.models import NodeLog

import markdown
from markdown.extensions import codehilite, fenced_code, wikilinks
from modularodm import fields

from framework.forms.utils import sanitize
from framework.guid.model import GuidStoredObject
from framework.mongo import utils as mongo_utils

from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.wiki import utils as wiki_utils
from website.addons.wiki.settings import WIKI_CHANGE_DATE
from website.project.commentable import Commentable
from website.project.model import Node
from website.project.signals import write_permissions_revoked
from website.util import api_v2_url

from website.exceptions import NodeStateError

from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
)


logger = logging.getLogger(__name__)


class AddonWikiNodeSettings(AddonNodeSettingsBase):

    complete = True
    has_auth = True
    is_publicly_editable = fields.BooleanField(default=False, index=True)

    def set_editing(self, permissions, auth=None, log=False):
        """Set the editing permissions for this node.

        :param auth: All the auth information including user, API key
        :param bool permissions: True = publicly editable
        :param bool save: Whether to save the privacy change
        :param bool log: Whether to add a NodeLog for the privacy change
            if true the node object is also saved
        """
        node = self.owner

        if permissions and not self.is_publicly_editable:
            if node.is_public:
                self.is_publicly_editable = True
            else:
                raise NodeStateError('Private components cannot be made publicly editable.')
        elif not permissions and self.is_publicly_editable:
            self.is_publicly_editable = False
        else:
            raise NodeStateError('Desired permission change is the same as current setting.')

        if log:
            node.add_log(
                action=(NodeLog.MADE_WIKI_PUBLIC
                        if self.is_publicly_editable
                        else NodeLog.MADE_WIKI_PRIVATE),
                params={
                    'project': node.parent_id,
                    'node': node._primary_key,
                },
                auth=auth,
                save=False,
            )
            node.save()

        self.save()

    def after_fork(self, node, fork, user, save=True):
        """Copy wiki settings and wiki pages to forks."""
        NodeWikiPage.clone_wiki_versions(node, fork, user, save)
        return super(AddonWikiNodeSettings, self).after_fork(node, fork, user, save)

    def after_register(self, node, registration, user, save=True):
        """Copy wiki settings and wiki pages to registrations."""
        NodeWikiPage.clone_wiki_versions(node, registration, user, save)
        clone = self.clone()
        clone.owner = registration
        if save:
            clone.save()
        return clone, None

    def after_set_privacy(self, node, permissions):
        """

        :param Node node:
        :param str permissions:
        :return str: Alert message

        """
        if permissions == 'private':
            if self.is_publicly_editable:
                self.set_editing(permissions=False, log=False)
                return (
                    'The wiki of {name} is now only editable by write contributors.'.format(
                        name=node.title,
                    )
                )

    def to_json(self, user):
        return {}


@write_permissions_revoked.connect
def subscribe_on_write_permissions_revoked(node):
    # Migrate every page on the node
    for wiki_name in node.wiki_private_uuids:
        wiki_utils.migrate_uuid(node, wiki_name)


def build_wiki_url(node, label, base, end):
    return '/{pid}/wiki/{wname}/'.format(pid=node._id, wname=label)


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


class NodeWikiPage(GuidStoredObject, Commentable):

    _id = fields.StringField(primary=True)

    page_name = fields.StringField(validate=validate_page_name)
    version = fields.IntegerField()
    date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    is_current = fields.BooleanField()
    content = fields.StringField(default='')

    user = fields.ForeignField('user')
    node = fields.ForeignField('node')

    # For Django compatibility
    @property
    def pk(self):
        return self._id

    @property
    def deep_url(self):
        return '{}wiki/{}/'.format(self.node.deep_url, urllib.quote(self.page_name))

    @property
    def url(self):
        return '{}wiki/{}/'.format(self.node.url, urllib.quote(self.page_name))

    @property
    def rendered_before_update(self):
        return self.date < WIKI_CHANGE_DATE

    # For Comment API compatibility
    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'wiki'

    @property
    def root_target_page(self):
        """The comment page type associated with NodeWikiPages."""
        return 'wiki'

    @property
    def is_deleted(self):
        key = mongo_utils.to_mongo_key(self.page_name)
        return key not in self.node.wiki_pages_current

    @property
    def absolute_api_v2_url(self):
        path = '/wikis/{}/'.format(self._id)
        return api_v2_url(path)

    def belongs_to_node(self, node_id):
        """Check whether the wiki is attached to the specified node."""
        return self.node._id == node_id

    def get_extra_log_params(self, comment):
        return {'wiki': {'name': self.page_name, 'url': comment.get_comment_page_url()}}

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

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
            sharejs_date = datetime.datetime.utcfromtimestamp(sharejs_timestamp)

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

    def clone_wiki(self, node_id):
        """Clone a node wiki page.
        :param node: The Node of the cloned wiki page
        :return: The cloned wiki page
        """
        node = Node.load(node_id)
        if not node:
            raise ValueError('Invalid node')
        clone = self.clone()
        clone.node = node
        clone.user = self.user
        clone.save()
        return clone

    @classmethod
    def clone_wiki_versions(cls, node, copy, user, save=True):
        """Clone wiki pages for a forked or registered project.
        :param node: The Node that was forked/registered
        :param copy: The fork/registration
        :param user: The user who forked or registered the node
        :param save: Whether to save the fork/registration
        :return: copy
        """
        copy.wiki_pages_versions = {}
        copy.wiki_pages_current = {}

        for key in node.wiki_pages_versions:
            copy.wiki_pages_versions[key] = []
            for wiki_id in node.wiki_pages_versions[key]:
                node_wiki = NodeWikiPage.load(wiki_id)
                cloned_wiki = node_wiki.clone_wiki(copy._id)
                copy.wiki_pages_versions[key].append(cloned_wiki._id)
                if node_wiki.is_current:
                    copy.wiki_pages_current[key] = cloned_wiki._id
        if save:
            copy.save()
        return copy
