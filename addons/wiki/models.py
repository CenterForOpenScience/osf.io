# -*- coding: utf-8 -*-
import datetime
import functools
import logging

import markdown
import pytz
from django.db.models.expressions import F
from django.db.models.aggregates import Max
from django.core.exceptions import ValidationError
from django.utils import timezone
from framework.auth.core import Auth
from addons.base.models import BaseNodeSettings
from bleach.callbacks import nofollow
from bleach import Cleaner
from functools import partial
from bleach.linkifier import LinkifyFilter
from django.db import models
from framework.forms.utils import sanitize
from markdown.extensions import codehilite, fenced_code, wikilinks
from osf.models import NodeLog, OSFUser, Comment
from osf.models.base import BaseModel, GuidMixin, ObjectIDMixin
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.requests import DummyRequest, get_request_and_user_id
from osf.exceptions import NodeStateError
from addons.wiki import utils as wiki_utils
from addons.wiki.exceptions import (
    PageCannotRenameError,
    PageConflictError,
)
from website.util import api_v2_url
from website.files.exceptions import VersionNotFoundError
from website import settings
from osf.utils.requests import get_headers_from_request

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


class WikiVersionNodeManager(models.Manager):

    def get_for_node(self, node, name=None, version=None, id=None):
        if name:
            wiki_page = WikiPage.objects.get_for_node(node, name)
            if not wiki_page:
                return None

            if version == 'previous':
                version = wiki_page.current_version_number - 1
            elif version == 'current' or version is None:
                version = wiki_page.current_version_number
            elif not ((isinstance(version, int) or version.isdigit())):
                return None

            try:
                return wiki_page.get_version(version=version)
            except WikiVersion.DoesNotExist:
                return None
        return WikiVersion.load(id)


class WikiVersion(ObjectIDMixin, BaseModel):
    objects = WikiVersionNodeManager()

    user = models.ForeignKey('osf.OSFUser', null=True, blank=True, on_delete=models.CASCADE)
    wiki_page = models.ForeignKey('WikiPage', null=True, blank=True, on_delete=models.CASCADE, related_name='versions')
    content = models.TextField(default='', blank=True)
    identifier = models.IntegerField(default=1)

    @property
    def is_current(self):
        return not self.wiki_page.deleted and self.id == self.wiki_page.versions.order_by('-created').first().id

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

    @property
    def rendered_before_update(self):
        return self.created < WIKI_CHANGE_DATE

    def get_draft(self, node):
        """
        Return most recently edited version of wiki, whether that is the
        last saved version or the most recent sharejs draft.
        """

        db = wiki_utils.share_db()
        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, self.wiki_page.page_name)

        doc_item = db['docs'].find_one({'_id': sharejs_uuid})
        if doc_item:
            sharejs_version = doc_item['_v']
            sharejs_timestamp = doc_item['_m']['mtime']
            sharejs_timestamp /= 1000  # Convert to appropriate units
            sharejs_date = datetime.datetime.utcfromtimestamp(sharejs_timestamp).replace(tzinfo=pytz.utc)

            if sharejs_version > 1 and sharejs_date > self.created:
                return doc_item['_data']

        return self.content

    def save(self, *args, **kwargs):
        rv = super(WikiVersion, self).save(*args, **kwargs)
        if self.wiki_page.node:
            self.wiki_page.node.update_search()
        self.wiki_page.modified = self.created
        self.wiki_page.save()
        self.check_spam()
        return rv

    def check_spam(self):
        request, user_id = get_request_and_user_id()
        user = OSFUser.load(user_id)
        if not isinstance(request, DummyRequest):
            request_headers = {
                k: v
                for k, v in get_headers_from_request(request).items()
                if isinstance(v, str)
            }

        node = self.wiki_page.node

        if not settings.SPAM_CHECK_ENABLED:
            return False
        if settings.SPAM_CHECK_PUBLIC_ONLY and not node.is_public:
            return False
        if 'ham_confirmed' in user.system_tags:
            return False

        content = self._get_spam_content(node)
        if not content:
            return
        is_spam = node.do_check_spam(
            user.fullname,
            user.username,
            content,
            request_headers
        )

        logger.info("Node ({}) '{}' smells like {} (tip: {})".format(
            node._id, node.title.encode('utf-8'), 'SPAM' if is_spam else 'HAM', node.spam_pro_tip
        ))
        if is_spam:
            node._check_spam_user(user)
        return is_spam

    def _get_spam_content(self, node):
        content = []
        content.append(self.raw_text(node).encode('utf-8'))
        if not content:
            return None
        return ' '.join(content)

    def clone_version(self, wiki_page, user):
        """Clone a node wiki page.
        :param wiki_page: The wiki_page you want attached to the clone.
        :return: The cloned wiki version
        """
        clone = self.clone()
        clone.wiki_page = wiki_page
        clone.user = user
        clone.save()
        return clone

    @property
    def absolute_api_v2_url(self):
        path = '/wiki_versions/{}/'.format(self._id)
        return api_v2_url(path)

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

class WikiPageNodeManager(models.Manager):

    def create_for_node(self, node, name, content, auth):
        existing_wiki_page = WikiPage.objects.get_for_node(node, name)
        if existing_wiki_page:
            raise NodeStateError('Wiki Page already exists.')

        wiki_page = WikiPage.objects.create(
            node=node,
            page_name=name,
            user=auth.user
        )
        # Creates a WikiVersion object
        wiki_page.update(auth.user, content)
        return wiki_page

    def get_for_node(self, node, name=None, id=None):
        if name:
            try:
                name = (name or '').strip()
                return WikiPage.objects.get(page_name__iexact=name, deleted__isnull=True, node=node)
            except WikiPage.DoesNotExist:
                return None
        return WikiPage.load(id)

    def get_wiki_pages_latest(self, node):
        wiki_page_ids = node.wikis.filter(deleted__isnull=True).values_list('id', flat=True)
        return WikiVersion.objects.annotate(name=F('wiki_page__page_name'), newest_version=Max('wiki_page__versions__identifier')).filter(identifier=F('newest_version'), wiki_page__id__in=wiki_page_ids)

    def include_wiki_settings(self, node):
        """Check if node meets requirements to make publicly editable."""
        return node.get_descendants_recursive()

class WikiPage(GuidMixin, BaseModel):
    objects = WikiPageNodeManager()

    page_name = models.CharField(max_length=200, validators=[validate_page_name, ])
    user = models.ForeignKey('osf.OSFUser', null=True, blank=True, on_delete=models.CASCADE)
    node = models.ForeignKey('osf.AbstractNode', null=True, blank=True, on_delete=models.CASCADE, related_name='wikis')
    deleted = NonNaiveDateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['page_name', 'node'])
        ]

    def save(self, *args, **kwargs):
        rv = super(WikiPage, self).save(*args, **kwargs)
        if self.node and self.node.is_public:
            self.node.update_search()
        return rv

    def update(self, user, content):
        """
        Updates the wiki with the provided content by creating a new version

        :param user: The user that is updating the wiki
        :param content: Latest content for wiki
        """
        version = WikiVersion(user=user, wiki_page=self, content=content, identifier=self.current_version_number + 1)
        version.save()

        self.node.add_log(
            action=NodeLog.WIKI_UPDATED,
            params={
                'project': self.node.parent_id,
                'node': self.node._primary_key,
                'page': self.page_name,
                'page_id': self._primary_key,
                'version': version.identifier,
            },
            auth=Auth(user),
            log_date=version.created,
            save=True
        )
        return version

    def update_active_sharejs(self, node):
        """
        Update all active sharejs sessions with latest wiki content.
        """

        """
        TODO: This def is meant to be used after updating wiki content via
        the v2 API, once updating has been implemented. It should be removed
        if not used for that purpose.
        """

        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, self.page_name)
        contributors = [user._id for user in node.contributors]
        wiki_utils.broadcast_to_sharejs('reload',
                                        sharejs_uuid,
                                        data=contributors)

    def belongs_to_node(self, node_id):
        """Check whether the wiki is attached to the specified node."""
        return self.node._id == node_id

    @property
    def current_version_number(self):
        return self.versions.order_by('-created').values_list('identifier', flat=True).first() or 0

    @property
    def url(self):
        return u'{}wiki/{}/'.format(self.node.url, self.page_name)

    def get_version(self, version=None):
        if version:
            ret = self.versions.filter(identifier=version).order_by('-created').first()
            if not ret:
                raise VersionNotFoundError(version)
            return ret
        else:
            return self.versions.order_by('-created').first()

    def get_versions(self):
        return self.versions.all().order_by('-created')

    @property
    def root_target_page(self):
        """The comment page type associated with WikiPages."""
        return 'wiki'

    @property
    def deep_url(self):
        return u'{}wiki/{}/'.format(self.node.deep_url, self.page_name)

    def clone_wiki_page(self, copy, user, save=True):
        """Clone a wiki page.
        :param node: The Node of the cloned wiki page
        :return: The cloned wiki page
        """
        new_wiki_page = self.clone()
        new_wiki_page.node = copy
        new_wiki_page.user = user
        new_wiki_page.save()
        for version in self.versions.all().order_by('created'):
            new_version = version.clone_version(new_wiki_page, user)
            if save:
                new_version.save()
        return

    @classmethod
    def clone_wiki_pages(cls, node, copy, user, save=True):
        """Clone wiki pages for a forked or registered project.
        First clones the WikiPage, then clones all WikiPage versions.
        :param node: The Node that was forked/registered
        :param copy: The fork/registration
        :param user: The user who forked or registered the node
        :param save: Whether to save the fork/registration
        :return: copy
        """
        for wiki_page in node.wikis.filter(deleted__isnull=True):
            wiki_page.clone_wiki_page(copy, user, save)
        return copy

    def to_json(self, user):
        return {}

    def get_extra_log_params(self, comment):
        return {'wiki': {'name': self.page_name, 'url': comment.get_comment_page_url()}}

    # For Comment API compatibility
    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'wiki'

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_api_v2_url(self):
        path = '/wikis/{}/'.format(self._id)
        return api_v2_url(path)

    def rename(self, new_name, auth):
        """
        Rename the wiki page with the new_name. Logs this information to the wiki's node.

        :param new_name: A string, the new page's name, e.g. ``"My Renamed Page"``.
        :param auth: All the auth information including user, API key.
        """
        new_name = (new_name or '').strip()
        existing_wiki_page = WikiPage.objects.get_for_node(self.node, new_name)
        key = wiki_utils.to_mongo_key(self.page_name)
        new_key = wiki_utils.to_mongo_key(new_name)

        if key == 'home':
            raise PageCannotRenameError('Cannot rename wiki home page')
        if (existing_wiki_page and not existing_wiki_page.deleted and key != new_key) or new_key == 'home':
            raise PageConflictError(
                'Page already exists with name {0}'.format(
                    new_name,
                )
            )

        # rename the page first in case we hit a validation exception.
        old_name = self.page_name
        self.page_name = new_name

        # TODO: merge historical records like update (prevents log breaks)
        # transfer the old page versions/current keys to the new name.
        if key != new_key:
            if key in self.node.wiki_private_uuids:
                self.node.wiki_private_uuids[new_key] = self.node.wiki_private_uuids[key]
                del self.node.wiki_private_uuids[key]

        self.node.add_log(
            action=NodeLog.WIKI_RENAMED,
            params={
                'project': self.node.parent_id,
                'node': self.node._primary_key,
                'page': self.page_name,
                'page_id': self._primary_key,
                'old_page': old_name,
                'version': self.current_version_number,
            },
            auth=auth,
            save=True,
        )
        self.save()
        return self

    def delete(self, auth):
        """
        Marks the wiki as deleted by setting the deleted field to the current datetime.
        Logs this information to the wiki's node.

        :param auth: All the auth information including user, API key.
        """
        if self.page_name.lower() == 'home':
            raise ValidationError('The home wiki page cannot be deleted.')
        self.deleted = timezone.now()

        Comment.objects.filter(root_target=self.guids.first()).update(root_target=None)

        self.node.add_log(
            action=NodeLog.WIKI_DELETED,
            params={
                'project': self.node.parent_id,
                'node': self.node._primary_key,
                'page': self.page_name,
                'page_id': self._primary_key,
            },
            auth=auth,
            save=True,
        )
        return self.save()


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
        WikiPage.clone_wiki_pages(node, fork, user, save)
        return super(NodeSettings, self).after_fork(node, fork, user, save)

    def after_register(self, node, registration, user, save=True):
        """Copy wiki settings and wiki pages to registrations."""
        WikiPage.clone_wiki_pages(node, registration, user, save)
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
