# -*- coding: utf-8 -*-
import datetime
import functools
import logging

import markdown
import pytz
from addons.base.models import BaseNodeSettings
from bleach.callbacks import nofollow
from bleach import Cleaner
from functools import partial
from bleach.linkifier import LinkifyFilter
from django.db import models
from framework.forms.utils import sanitize
from markdown.extensions import codehilite, fenced_code, wikilinks
from osf.models import AbstractNode, NodeLog
from osf.models.base import BaseModel, GuidMixin
from osf.utils.fields import NonNaiveDateTimeField
from website import settings
from addons.wiki import utils as wiki_utils
from website.exceptions import NodeStateError
from website.util import api_v2_url

from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
)

logger = logging.getLogger(__name__)

SHAREJS_HOST = 'localhost'
SHAREJS_PORT = 7007
SHAREJS_URL = '{}:{}'.format(SHAREJS_HOST, SHAREJS_PORT)

SHAREJS_DB_NAME = 'sharejs'
SHAREJS_DB_URL = 'mongodb://{}:{}/{}'.format(settings.DB_HOST, settings.DB_PORT, SHAREJS_DB_NAME)

# TODO: Change to release date for wiki change
WIKI_CHANGE_DATE = datetime.datetime.utcfromtimestamp(1423760098).replace(tzinfo=pytz.utc)

def validate_page_name(value):
    value = (value or '').strip()

    if not value:
        # TODO: determine if this if possible anymore, deprecate if not
        raise NameEmptyError('Page name cannot be blank.')
    if value.find('/') != -1:
        raise NameInvalidError('Page name cannot contain forward slashes.')
    if len(value) > 100:
        raise NameMaximumLengthError('Page name cannot be greater than 100 characters.')
    return True

def build_html_output(content, node):
    return markdown.markdown(
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

def render_content(content, node):
    html_output = build_html_output(content, node)

    # linkify gets called after santize, because we're adding rel="nofollow"
    #   to <a> elements - but don't want to allow them for other elements.
    sanitized_content = sanitize(html_output, **settings.WIKI_WHITELIST)
    return sanitized_content


def build_wiki_url(node, label, base, end):
    return '/{pid}/wiki/{wname}/'.format(pid=node._id, wname=label)


class NodeWikiPage(GuidMixin, BaseModel):
    page_name = models.CharField(max_length=200, validators=[validate_page_name, ])
    version = models.IntegerField(default=1)
    date = NonNaiveDateTimeField(auto_now_add=True)
    content = models.TextField(default='', blank=True)
    user = models.ForeignKey('osf.OSFUser', null=True, blank=True, on_delete=models.CASCADE)
    node = models.ForeignKey('osf.AbstractNode', null=True, blank=True, on_delete=models.CASCADE)

    @property
    def is_current(self):
        key = wiki_utils.to_mongo_key(self.page_name)
        if key in self.node.wiki_pages_current:
            return self.node.wiki_pages_current[key] == self._id
        else:
            return False

    @property
    def deep_url(self):
        return u'{}wiki/{}/'.format(self.node.deep_url, self.page_name)

    @property
    def url(self):
        return u'{}wiki/{}/'.format(self.node.url, self.page_name)

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
        key = wiki_utils.to_mongo_key(self.page_name)
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
        html_output = build_html_output(self.content, node=node)
        try:
            cleaner = Cleaner(
                tags=settings.WIKI_WHITELIST['tags'],
                attributes=settings.WIKI_WHITELIST['attributes'],
                styles=settings.WIKI_WHITELIST['styles'],
                filters=[partial(LinkifyFilter, callbacks=[nofollow, ])]
            )

            return cleaner.clean(html_output)
        except TypeError:
            logger.warning('Returning unlinkified content.')
            return render_content(self.content, node=node)

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
            sharejs_timestamp /= 1000  # Convert to appropriate units
            sharejs_date = datetime.datetime.utcfromtimestamp(sharejs_timestamp).replace(tzinfo=pytz.utc)

            if sharejs_version > 1 and sharejs_date > self.date:
                return doc_item['_data']

        return self.content

    def update_active_sharejs(self, node):
        """
        Update all active sharejs sessions with latest wiki content.
        """

        """
        TODO: This def is meant to be used after updating wiki content via
        the v2 API, once updating is has been implemented. It should be removed
        if not used for that purpose.
        """

        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, self.page_name)
        contributors = [user._id for user in node.contributors]
        wiki_utils.broadcast_to_sharejs('reload',
                                        sharejs_uuid,
                                        data=contributors)

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
        node = AbstractNode.load(node_id)
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


class NodeSettings(BaseNodeSettings):
    complete = True
    has_auth = True
    is_publicly_editable = models.BooleanField(default=False, db_index=True)

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
                save=True,
            )

        self.save()

    def after_fork(self, node, fork, user, save=True):
        """Copy wiki settings and wiki pages to forks."""
        NodeWikiPage.clone_wiki_versions(node, fork, user, save)
        return super(NodeSettings, self).after_fork(node, fork, user, save)

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
