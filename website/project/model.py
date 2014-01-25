# -*- coding: utf-8 -*-
import subprocess
import uuid
import hashlib
import calendar
import datetime
import os
import re
import unicodedata
import urllib
import urlparse
import logging

import pytz
from dulwich.repo import Repo
from dulwich.object_store import tree_lookup_path

from framework import status
from framework.mongo import ObjectId
from framework.mongo.utils import to_mongo
from framework.auth import get_user, User
from framework.analytics import (
    get_basic_counters, increment_user_activity_counters, piwik
)
from framework.git.exceptions import FileNotModified
from framework import StoredObject, fields, utils
from framework.search.solr import update_solr, delete_solr_doc
from framework import GuidStoredObject, Q
from framework.addons import AddonModelMixin
from framework import session
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website import settings

def utc_datetime_to_timestamp(dt):
    return float(
        str(calendar.timegm(dt.utcnow().utctimetuple())) + '.' + str(dt.microsecond)
    )


def normalize_unicode(ustr):
    return unicodedata.normalize('NFKD', ustr)\
        .encode('ascii', 'ignore')


class MetaSchema(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    name = fields.StringField()
    schema = fields.DictionaryField()
    category = fields.StringField()

    # Version of the Knockout metadata renderer to use (e.g. if data binds
    # change)
    metadata_version = fields.IntegerField()
    # Version of the schema to use (e.g. if questions, responses change)
    schema_version = fields.IntegerField()


def ensure_schemas(clear=True):
    """Import meta-data schemas from JSON to database, optionally clearing
    database first.

    :param clear: Clear schema database before import

    """
    if clear:
        MetaSchema.remove()
    for schema in OSF_META_SCHEMAS:
        try:
            MetaSchema.find_one(
                Q('name', 'eq', schema['name']) &
                Q('schema_version', 'eq', schema['schema_version'])
            )
        except:
            schema['name'] = schema['name'].replace(' ', '_')
            schema_obj = MetaSchema(**schema)
            schema_obj.save()


class MetaData(GuidStoredObject):

    _id = fields.StringField()
    target = fields.AbstractForeignField(backref='annotated')

    # Annotation category: Comment, review, registration, etc.
    category = fields.StringField()

    # Annotation data
    schema = fields.ForeignField('MetaSchema')
    payload = fields.DictionaryField()

    # Annotation provenance
    user = fields.ForeignField('User', backref='annotated')
    date = fields.DateTimeField(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        super(MetaData, self).__init__(*args, **kwargs)
        if self.category and not self.schema:
            if self.category in OSF_META_SCHEMAS:
                self.schema = self.category


class ApiKey(StoredObject):

    # The key is also its primary key
    _id = fields.StringField(
        primary=True,
        default=lambda: str(ObjectId()) + str(uuid.uuid4())
    )
    # A display name
    label = fields.StringField()

    @property
    def user(self):
        return self.user__keyed[0] if self.user__keyed else None

    @property
    def node(self):
        return self.node__keyed[0] if self.node__keyed else None


class NodeLog(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    date = fields.DateTimeField(default=datetime.datetime.utcnow)
    action = fields.StringField()
    params = fields.DictionaryField()

    user = fields.ForeignField('user', backref='created')
    api_key = fields.ForeignField('apikey', backref='created')
    foreign_user = fields.StringField()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    # Log action constants
    PROJECT_CREATED = 'project_created'
    NODE_CREATED = 'node_created'
    NODE_REMOVED = 'node_removed'
    WIKI_UPDATED = 'wiki_updated'
    CONTRIB_ADDED = 'contributor_added'
    CONTRIB_REMOVED = 'contributor_removed'
    MADE_PUBLIC = 'made_public'
    MADE_PRIVATE = 'made_private'
    TAG_ADDED = 'tag_added'
    TAG_REMOVED = 'tag_removed'
    EDITED_TITLE = 'edit_title'
    EDITED_DESCRIPTION = 'edit_description'
    PROJECT_REGISTERED = 'project_registered'
    FILE_ADDED = 'file_added'
    FILE_REMOVED = 'file_removed'
    FILE_UPDATED = 'file_updated'
    NODE_FORKED = 'node_forked'

    @property
    def node(self):
        return Node.load(self.params.get('node')) or \
            Node.load(self.params.get('project'))

    @property
    def tz_date(self):
        '''Return the timezone-aware date.
        '''
        # Date should always be defined, but a few logs in production are
        # missing dates; return None and log error if date missing
        if self.date:
            return self.date.replace(tzinfo=pytz.UTC)
        logging.error('Date missing on NodeLog {}'.format(self._primary_key))

    @property
    def formatted_date(self):
        '''Return the timezone-aware, ISO-formatted string representation of
        this log's date.
        '''
        if self.tz_date:
            return self.tz_date.isoformat()

    def _render_log_contributor(self, contributor):
        if isinstance(contributor, dict):
            rv = contributor.copy()
            rv.update({'registered': False})
            return rv
        user = User.load(contributor)
        return {
            'id': user._primary_key,
            'fullname': user.fullname,
            'registered': True,
        }

    # TODO: Move to separate utility function
    def serialize(self):
        '''Return a dictionary representation of the log.'''
        return {
            'id': str(self._primary_key),
            'user': self.user.serialize()
                    if isinstance(self.user, User)
                    else {'fullname': self.foreign_user},
            'contributors': [self._render_log_contributor(c) for c in self.params.get("contributors", [])],
            'contributor': self._render_log_contributor(self.params.get("contributor", {})),
            'api_key': self.api_key.label if self.api_key else '',
            'action': self.action,
            'params': self.params,
            'date': utils.rfcformat(self.date),
            'node': self.node.serialize() if self.node else None
        }


class Tag(StoredObject):

    _id = fields.StringField(primary=True)
    count_public = fields.IntegerField(default=0)
    count_total = fields.IntegerField(default=0)

    @property
    def url(self):
        return '/search/?q=tags:{}'.format(self._id)


class Node(GuidStoredObject, AddonModelMixin):

    redirect_mode = 'proxy'

    # Node fields that trigger an update to Solr on save
    SOLR_UPDATE_FIELDS = {
        'title',
        'category',
        'description',
        'contributors',
        'tags',
        'is_fork',
        'is_registration',
        'is_public',
        'is_deleted',
        'wiki_pages_current',
    }

    _id = fields.StringField(primary=True)

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)

    # Permissions
    is_public = fields.BooleanField(default=False)

    is_deleted = fields.BooleanField(default=False)
    deleted_date = fields.DateTimeField()

    is_registration = fields.BooleanField(default=False)
    registered_date = fields.DateTimeField()
    registered_user = fields.ForeignField('user', backref='registered')
    registered_schema = fields.ForeignField('metaschema', backref='registered')
    registered_meta = fields.DictionaryField()

    is_fork = fields.BooleanField(default=False)
    forked_date = fields.DateTimeField()

    title = fields.StringField(versioned=True)
    description = fields.StringField()
    category = fields.StringField()

    registration_list = fields.StringField(list=True)
    fork_list = fields.StringField(list=True)
    private_links = fields.StringField(list=True)

    # TODO: move these to NodeFile
    files_current = fields.DictionaryField()
    files_versions = fields.DictionaryField()
    wiki_pages_current = fields.DictionaryField()
    wiki_pages_versions = fields.DictionaryField()

    creator = fields.ForeignField('user', backref='created')
    contributors = fields.ForeignField('user', list=True, backref='contributed')
    # Dict list that includes registered AND unregsitered users
    # Example: [{u'id': u've4nx'}, {u'nr_name': u'Joe Dirt', u'nr_email': u'joe@example.com'}]
    contributor_list = fields.DictionaryField(list=True)
    users_watching_node = fields.ForeignField('user', list=True, backref='watched')

    logs = fields.ForeignField('nodelog', list=True, backref='logged')
    tags = fields.ForeignField('tag', list=True, backref='tagged')

    nodes = fields.ForeignField('node', list=True, backref='parent')
    forked_from = fields.ForeignField('node', backref='forked')
    registered_from = fields.ForeignField('node', backref='registrations')

    api_keys = fields.ForeignField('apikey', list=True, backref='keyed')

    piwik_site_id = fields.StringField()

    ## Meta-data
    #comment_schema = OSF_META_SCHEMAS['osf_comment']

    _meta = {'optimistic': True}

    def __init__(self, *args, **kwargs):

        super(Node, self).__init__(*args, **kwargs)

        # Crash if parent provided and not project
        project = kwargs.get('project')
        if project and project.category != 'project':
            raise ValueError('Parent must be a project.')

        if kwargs.get('_is_loaded', False):
            return

        if self.creator:
            self.contributors.append(self.creator)
            self.contributor_list.append({'id': self.creator._primary_key})

    def can_edit(self, user, api_key=None):
        return (
            self.is_contributor(user)
            or (api_key is not None and self is api_key.node)
            or (bool(user) and user == self.creator)
        )

    def can_view(self, user, link='', api_key=None):
        if session:
            key_ring = set(session.data['link'])
            return self.is_public or self.can_edit(user, api_key) \
                or not key_ring.isdisjoint(self.private_links)
        else:
            return self.is_public or self.can_edit(user, api_key) \
                or link in self.private_links

    @property
    def has_files(self):
        """Check whether the node has any add-ons or components that define
        the files interface. Overrides AddonModelMixin::has_files to include
        recursion over child nodes.

        :return bool: Has files add-ons

        """
        rv = super(Node, self).has_files
        if rv:
            return rv
        for child in self.nodes:
            if child.has_files:
                return True
        return False

    def save(self, *args, **kwargs):

        first_save = not self._is_loaded
        is_original = not self.is_registration and not self.is_fork

        saved_fields = super(Node, self).save(*args, **kwargs)

        if first_save and is_original:

            #
            for addon in settings.ADDONS_AVAILABLE:
                if addon.added_to['node']:
                    self.add_addon(addon.short_name)

            #
            if getattr(self, 'project', None):

                # Append log to parent
                self.project.nodes.append(self)
                self.project.save()

                # Define log fields for component
                log_action = NodeLog.NODE_CREATED
                log_params = {
                    'node': self._primary_key,
                    'project': self.project._primary_key,
                }

            else:

                # Define log fields for non-component project
                log_action = NodeLog.PROJECT_CREATED
                log_params = {
                    'project': self._primary_key,
                }

            # Add log with appropriate fields
            self.add_log(
                log_action,
                params=log_params,
                user=self.creator,
                log_date=self.date_created,
                save=True,
            )

        # Only update Solr if at least one stored field has changed, and if
        # public or privacy setting has changed
        update_solr = bool(self.SOLR_UPDATE_FIELDS.intersection(saved_fields))
        if not self.is_public:
            if first_save or 'is_public' not in saved_fields:
                update_solr = False
        if update_solr:
            self.update_solr()

        # This method checks what has changed.
        if settings.PIWIK_HOST:
            piwik.update_node(self, saved_fields)

        # Return expected value for StoredObject::save
        return saved_fields

    def get_recent_logs(self, n=10):
        '''Return a list of the n most recent logs, in reverse chronological
        order.
        '''
        return list(reversed(self.logs)[:n])

    @property
    def date_modified(self):
        '''The most recent datetime when this node was modified, based on
        the logs.
        '''
        try:
            return self.logs[-1].date
        except IndexError:
            return None

    def set_title(self, title, user, api_key=None, save=False):
        """Set the title of this Node and log it.

        :param str title: The new title.
        :param User user: User who made the action.
        :param ApiKey api_key: Optional API key.

        """
        original_title = self.title
        self.title = title
        self.add_log(
            action=NodeLog.EDITED_TITLE,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'title_new': self.title,
                'title_original': original_title,
            },
            user=user,
            api_key=api_key,
        )
        if save:
            self.save()
        return None

    def set_description(self, description, user, api_key=None, save=False):
        """Set the description and log the event.

        :param str description: The new description
        :param User user: The user who changed the description.
        :param ApiKey api_key: Optional API key.
        :param bool save: Save self after updating.

        """
        original = self.description
        self.description = description
        if save:
            self.save()
        self.add_log(
            action=NodeLog.EDITED_DESCRIPTION,
            params={
                'project': self.parent,  # None if no parent
                'node': self._primary_key,
                'description_new': self.description,
                'description_original': original
            },
            user=user,
            api_key=api_key
        )
        return None

    def update_solr(self):
        """Send the current state of the object to Solr, or delete it from Solr
        as appropriate.

        """
        if not settings.USE_SOLR:
            return

        from website.addons.wiki.model import NodeWikiPage

        if self.category == 'project':
            # All projects use their own IDs.
            solr_document_id = self._id
        else:
            try:
                # Components must have a project for a parent; use its ID.
                solr_document_id = self.parent_id
            except IndexError:
                # Skip orphaned components. There are some in the DB...
                return

        if self.is_deleted or not self.is_public:
            # If the Node is deleted *or made private*
            # Delete or otherwise ensure the Solr document doesn't exist.
            delete_solr_doc({
                'doc_id': solr_document_id,
                '_id': self._id,
            })
        else:
            # Insert/Update the Solr document
            solr_document = {
                'id': solr_document_id,
                #'public': self.is_public,
                '{}_contributors'.format(self._id): [
                    x.fullname for x in self.contributors
                ],
                '{}_contributors_url'.format(self._id): [
                    x.profile_url for x in self.contributors
                ],
                '{}_title'.format(self._id): self.title,
                '{}_category'.format(self._id): self.category,
                '{}_public'.format(self._id): self.is_public,
                '{}_tags'.format(self._id): [x._id for x in self.tags],
                '{}_description'.format(self._id): self.description,
                '{}_url'.format(self._id): self.url,
                }

            # TODO: Move to wiki add-on
            for wiki in [
                NodeWikiPage.load(x)
                for x in self.wiki_pages_current.values()
            ]:
                solr_document.update({
                    '__'.join((self._id, wiki.page_name, 'wiki')): wiki.raw_text
                })

            update_solr(solr_document)

    def remove_node(self, user, api_key=None, date=None, top=True):
        """Remove node and recursively remove its children. Does not remove
        nodes from database; instead, removed nodes are flagged as deleted.
        Git repos are also not deleted. Adds a log to the parent node if top
        is True.

        :param user: User removing the node
        :param api_key: API key used to remove the node
        :param date: Date node was removed
        :param top: Is this the first node being removed?

        """
        if not self.can_edit(user, api_key):
            return False

        date = date or datetime.datetime.utcnow()

        # Remove child nodes
        for node in self.nodes:
            if not node.category == 'project':
                if not node.remove_node(user, api_key, date=date, top=False):
                    return False

        # Add log to parent
        if top and self.node__parent:
            self.node__parent[0].add_log(
                NodeLog.NODE_REMOVED,
                params={
                    'project': self._primary_key,
                },
                user=user,
                log_date=datetime.datetime.utcnow(),
            )

        # Remove self from parent registration list
        if self.is_registration:
            try:
                self.registered_from.registration_list.remove(self._primary_key)
                self.registered_from.save()
            except ValueError:
                pass

        # Remove self from parent fork list
        if self.is_fork:
            try:
                self.forked_from.fork_list.remove(self._primary_key)
                self.forked_from.save()
            except ValueError:
                pass

        self.is_deleted = True
        self.deleted_date = date
        self.save()

        return True

    def fork_node(self, user, api_key=None, title='Fork of '):

        # todo: should this raise an error?
        if not self.can_view(user, api_key):
            return

        folder_old = os.path.join(settings.UPLOADS_PATH, self._primary_key)

        when = datetime.datetime.utcnow()

        original = self.load(self._primary_key)
        forked = original.clone()

        forked.logs = self.logs
        forked.tags = self.tags

        for node_contained in original.nodes:
            forked_node = node_contained.fork_node(user, api_key=api_key, title='')
            if forked_node is not None:
                forked.nodes.append(forked_node)

        forked.title = title + forked.title
        forked.is_fork = True
        forked.forked_date = when
        forked.forked_from = original
        forked.is_public = False
        forked.creator = user
        forked.contributor_list = []
        forked.private_links = []

        forked.add_contributor(user, log=False, save=False)

        forked.add_log(
            action=NodeLog.NODE_FORKED,
            params={
                'project': original.parent_id,
                'node': original._primary_key,
                'registration': forked._primary_key,
            },
            user=user,
            api_key=api_key,
            log_date=when,
            save=False,
        )

        forked.save()

        # After fork callback
        for addon in original.get_addons():
            _, message = addon.after_fork(original, forked, user)
            if message:
                status.push_status_message(message)

        if os.path.exists(folder_old):
            folder_new = os.path.join(settings.UPLOADS_PATH, forked._primary_key)
            Repo(folder_old).clone(folder_new)

        original.fork_list.append(forked._primary_key)
        original.save()

        return forked

    def register_node(self, schema, user, template, data, api_key=None):
        """Make a frozen copy of a node.

        :param schema: Schema object
        :param user: User registering the node
        :param api_key: API key registering the node
        :template: Template name
        :data: Form data

        """
        folder_old = os.path.join(settings.UPLOADS_PATH, self._primary_key)
        template = urllib.unquote_plus(template)
        template = to_mongo(template)

        when = datetime.datetime.utcnow()

        original = self.load(self._primary_key)
        registered = original.clone()

        registered.is_registration = True
        registered.registered_date = when
        registered.registered_user = user
        registered.registered_schema = schema
        registered.registered_from = original
        if not registered.registered_meta:
            registered.registered_meta = {}
        registered.registered_meta[template] = data

        registered.contributors = self.contributors
        registered.private_links = []
        registered.forked_from = self.forked_from
        registered.creator = self.creator
        registered.logs = self.logs
        registered.tags = self.tags

        registered.save()

        # After register callback
        for addon in original.get_addons():
            _, message = addon.after_register(original, registered, user)
            if message:
                status.push_status_message(message)

        if os.path.exists(folder_old):
            folder_new = os.path.join(settings.UPLOADS_PATH, registered._primary_key)
            Repo(folder_old).clone(folder_new)

        registered.nodes = []

        # todo: should be recursive; see Node.fork_node()
        for original_node_contained in original.nodes:

            if not original_node_contained.can_edit(user):
                # todo: inform user that node can't be registered
                continue

            node_contained = original_node_contained.clone()
            node_contained.save()

            folder_old = os.path.join(settings.UPLOADS_PATH, original_node_contained._primary_key)

            if os.path.exists(folder_old):
                folder_new = os.path.join(settings.UPLOADS_PATH, node_contained._primary_key)
                Repo(folder_old).clone(folder_new)

            node_contained.is_registration = True
            node_contained.registered_date = when
            node_contained.registered_user = user
            node_contained.registered_schema = schema
            node_contained.registered_from = original_node_contained
            if not node_contained.registered_meta:
                node_contained.registered_meta = {}
            node_contained.registered_meta[template] = data
            
            node_contained.contributors = original_node_contained.contributors
            node_contained.forked_from = original_node_contained.forked_from
            node_contained.creator = original_node_contained.creator
            node_contained.logs = original_node_contained.logs
            node_contained.tags = original_node_contained.tags
            node_contained.private_links = []

            node_contained.save()

            # After register callback
            for addon in original_node_contained.get_addons():
                _, message = addon.after_register(
                    original_node_contained, node_contained, user
                )
                if message:
                    status.push_status_message(message)

            registered.nodes.append(node_contained)

        original.add_log(
            action=NodeLog.PROJECT_REGISTERED,
            params={
                'project':original.parent_id,
                'node':original._primary_key,
                'registration':registered._primary_key,
            },
            user=user,
            api_key=api_key,
            log_date=when
        )
        original.registration_list.append(registered._id)
        original.save()

        registered.save()
        return registered

    def remove_tag(self, tag, user, api_key, save=True):
        if tag in self.tags:
            self.tags.remove(tag)
            self.add_log(
                action=NodeLog.TAG_REMOVED,
                params={
                    'project':self.parent_id,
                    'node':self._primary_key,
                    'tag':tag,
                },
                user=user,
                api_key=api_key
            )
            if save:
                self.save()

    def add_tag(self, tag, user, api_key, save=True):
        if tag not in self.tags:
            new_tag = Tag.load(tag)
            if not new_tag:
                new_tag = Tag(_id=tag)
            new_tag.count_total += 1
            if self.is_public:
                new_tag.count_public += 1
            new_tag.save()
            self.tags.append(new_tag)
            self.add_log(
                action=NodeLog.TAG_ADDED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'tag': tag,
                },
                user=user,
                api_key=api_key
            )
            if save:
                self.save()

    def get_file(self, path, version=None):
        from website.addons.osffiles.model import NodeFile
        if version is not None:
            folder_name = os.path.join(settings.UPLOADS_PATH, self._primary_key)
            if os.path.exists(os.path.join(folder_name, ".git")):
                file_object = NodeFile.load(self.files_versions[path.replace('.', '_')][version])
                repo = Repo(folder_name)
                tree = repo.commit(file_object.git_commit).tree
                (mode, sha) = tree_lookup_path(repo.get_object, tree, path)
                return repo[sha].data, file_object.content_type
        return None, None

    def get_file_object(self, path, version=None):
        from website.addons.osffiles.model import NodeFile
        if version is not None:
            directory = os.path.join(settings.UPLOADS_PATH, self._primary_key)
            if os.path.exists(os.path.join(directory, '.git')):
                return NodeFile.load(self.files_versions[path.replace('.', '_')][version])
            # TODO: Raise exception here
        return None, None # TODO: Raise exception here

    def remove_file(self, user, api_key, path):
        '''Removes a file from the filesystem, NodeFile collection, and does a git delete ('git rm <file>')

        :param user:
        :param path:

        :return: True on success, False on failure
        '''
        from website.addons.osffiles.model import NodeFile

        #FIXME: encoding the filename this way is flawed. For instance - foo.bar resolves to the same string as foo_bar.
        file_name_key = path.replace('.', '_')

        repo_path = os.path.join(settings.UPLOADS_PATH, self._primary_key)

        # TODO make sure it all works, otherwise rollback as needed
        # Do a git delete, which also removes from working filesystem.
        try:
            subprocess.check_output(
                ['git', 'rm', path],
                cwd=repo_path,
                shell=False
            )

            repo = Repo(repo_path)

            message = '{path} deleted'.format(path=path)
            committer = self._get_committer(user, api_key)

            commit_id = repo.do_commit(message, committer)

        except subprocess.CalledProcessError:
            return False

        # date_modified = datetime.datetime.now()

        if file_name_key in self.files_current:
            nf = NodeFile.load(self.files_current[file_name_key])
            nf.is_deleted = True
            # nf.date_modified = date_modified
            nf.save()
            self.files_current.pop(file_name_key, None)

        if file_name_key in self.files_versions:
            for i in self.files_versions[file_name_key]:
                nf = NodeFile.load(i)
                nf.is_deleted = True
                # nf.date_modified = date_modified
                nf.save()
            self.files_versions.pop(file_name_key)

        # Updates self.date_modified
        self.save()

        self.add_log(
            action=NodeLog.FILE_REMOVED,
            params={
                'project':self.parent_id,
                'node':self._primary_key,
                'path':path
            },
            user=user,
            api_key=api_key,
            log_date=nf.date_modified
        )

        # self.save()
        return True

    @staticmethod
    def _get_committer(user, api_key):

        if api_key:
            commit_key_msg = ':{}'.format(api_key.label)
            if api_key.user:
                commit_name = api_key.user.fullname
                commit_id = api_key.user._primary_key
                commit_category = 'user'
            if api_key.node:
                commit_name = api_key.node.title
                commit_id = api_key.node._primary_key
                commit_category = 'node'

        elif user:
            commit_key_msg = ''
            commit_name = user.fullname
            commit_id = user._primary_key
            commit_category = 'user'

        else:
            raise Exception('Must provide either user or api_key.')

        committer = u'{name}{key_msg} <{category}-{id}@openscienceframework.org>'.format(
            name=commit_name,
            key_msg=commit_key_msg,
            category=commit_category,
            id=commit_id,
        )

        committer = normalize_unicode(committer)

        return committer

    def add_file(self, user, api_key, file_name, content, size, content_type):
        """
        Instantiates a new NodeFile object, and adds it to the current Node as
        necessary.
        """
        from website.addons.osffiles.model import NodeFile
        # TODO: Reading the whole file into memory is not scalable. Fix this.

        # This node's folder
        folder_name = os.path.join(settings.UPLOADS_PATH, self._primary_key)

        # TODO: This should be part of the build phase, not here.
        # verify the upload root exists
        if not os.path.isdir(settings.UPLOADS_PATH):
            os.mkdir(settings.UPLOADS_PATH)

        # Make sure the upload directory contains a git repo.
        if os.path.exists(folder_name):
            if os.path.exists(os.path.join(folder_name, ".git")):
                repo = Repo(folder_name)
            else:
                # ... or create one
                repo = Repo.init(folder_name)
        else:
            # if the Node's folder isn't there, create it.
            os.mkdir(folder_name)
            repo = Repo.init(folder_name)

        # Is this a new file, or are we updating an existing one?
        file_is_new = not os.path.exists(os.path.join(folder_name, file_name))

        if not file_is_new:
            # Get the hash of the old file
            old_file_hash = hashlib.md5()
            with open(os.path.join(folder_name, file_name), 'rb') as f:
                for chunk in iter(
                        lambda: f.read(128 * old_file_hash.block_size),
                        b''
                ):
                    old_file_hash.update(chunk)

            # If the file hasn't changed
            if old_file_hash.digest() == hashlib.md5(content).digest():
                raise FileNotModified()

        # Write the content of the temp file into a new file
        with open(os.path.join(folder_name, file_name), 'wb') as f:
            f.write(content)

        # Deal with git
        repo.stage([file_name])

        committer = self._get_committer(user, api_key)

        commit_id = repo.do_commit(
            message=unicode(file_name +
                            (' added' if file_is_new else ' updated')),
            committer=committer,
        )

        # Deal with creating a NodeFile in the database
        node_file = NodeFile(
            path=file_name,
            filename=file_name,
            size=size,
            node=self,
            uploader=user,
            git_commit=commit_id,
            content_type=content_type,
        )
        node_file.save()

        # Add references to the NodeFile to the Node object
        file_name_key = node_file.clean_filename

        # Reference the current file version
        self.files_current[file_name_key] = node_file._primary_key

        # Create a version history if necessary
        if not file_name_key in self.files_versions:
            self.files_versions[file_name_key] = []

        # Add reference to the version history
        self.files_versions[file_name_key].append(node_file._primary_key)

        self.add_log(
            action=NodeLog.FILE_ADDED if file_is_new else NodeLog.FILE_UPDATED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'path': node_file.path,
                'version': len(self.files_versions)
            },
            user=user,
            api_key=api_key,
            log_date=node_file.date_uploaded
        )

        return node_file

    def add_private_link(self, link='', save=True):
        link = link or str(uuid.uuid4()).replace("-", "")
        self.private_links.append(link)
        if save:
            self.save()
        return link

    def remove_private_link(self, link, save=True):
        try:
            self.private_links.remove(link)
        except ValueError:
            pass
        if save:
            self.save()

    def add_log(self, action, params, user, foreign_user=None, api_key=None, log_date=None, save=True):
        log = NodeLog()
        log.action = action
        log.user = user
        log.foreign_user = foreign_user
        log.api_key = api_key
        if log_date:
            log.date=log_date
        log.params=params
        log.save()
        self.logs.append(log)
        if save:
            self.save()
        if user:
            increment_user_activity_counters(user._primary_key, action, log.date)
        if self.node__parent:
            parent = self.node__parent[0]
            parent.logs.append(log)
            parent.save()
        return log

    @property
    def url(self):
        return '/{}/'.format(self._primary_key)

    @property
    def absolute_url(self):
        if not self.url:
            logging.error("Node {0} has a parent that is not a project".format(self._id))
            return None
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    @property
    def api_url(self):
        if not self.url:
            logging.error("Node {0} has a parent that is not a project".format(self._id))
            return None
        return '/api/v1{0}'.format(self.deep_url)

    @property
    def deep_url(self):
        if self.category == 'project':
            return '/project/{}/'.format(self._primary_key)
        else:
            if self.node__parent and self.node__parent[0].category == 'project':
                return '/project/{}/node/{}/'.format(
                    self.parent_id,
                    self._primary_key
                )
        logging.error("Node {0} has a parent that is not a project".format(self._id))

    def author_list(self, and_delim='&'):
        author_names = [
            author.biblio_name
            for author in self.contributors
        ]
        if len(author_names) < 2:
            return ' {0} '.format(and_delim).join(author_names)
        if len(author_names) > 7:
            author_names = author_names[:7]
            author_names.append('et al.')
            return ', '.join(author_names)
        return u'{0}, {1} {2}'.format(
            ', '.join(author_names[:-1]),
            and_delim,
            author_names[-1]
        )

    @property
    def citation_apa(self):
        return u'{authors}, ({year}). {title}. Retrieved from Open Science Framework, <a href="{url}">{url}</a>'.format(
            authors=self.author_list(and_delim='&'),
            year=self.logs[-1].date.year,
            title=self.title,
            url=self.display_absolute_url,
        )

    @property
    def citation_mla(self):
        return u'{authors}. "{title}". Open Science Framework, {year}. <a href="{url}">{url}</a>'.format(
            authors=self.author_list(and_delim='and'),
            year=self.logs[-1].date.year,
            title=self.title,
            url=self.display_absolute_url,
        )

    @property
    def citation_chicago(self):
        return u'{authors}. "{title}". Open Science Framework ({year}). <a href="{url}">{url}</a>'.format(
            authors=self.author_list(and_delim='and'),
            year=self.logs[-1].date.year,
            title=self.title,
            url=self.display_absolute_url,
        )

    @property
    def parent(self):
        '''The parent node, if it exists, otherwise ``None``.'''
        try:
            if not self.node__parent[0].is_deleted:
                return self.node__parent[0]
        except IndexError:
            pass
        return None

    @property
    def watch_url(self):
        return os.path.join(self.api_url, "watch/")

    @property
    def parent_id(self):
        if self.node__parent:
            return self.node__parent[0]._primary_key
        return None

    @property
    def project_or_component(self):
        return 'project' if self.category == 'project' else 'component'

    def is_contributor(self, user):
        return (user is not None) and ((user in self.contributors) or user == self.creator)

    def remove_nonregistered_contributor(self, user, api_key, name, hash_id):
        deleted = False
        for idx, contrib in enumerate(self.contributor_list):
            if contrib.get('nr_name') == name and hashlib.md5(contrib.get('nr_email')).hexdigest() == hash_id:
                del self.contributor_list[idx]
                deleted = True
                break
        if not deleted:
            return False
        self.save()
        self.add_log(
            action=NodeLog.CONTRIB_REMOVED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'contributor': contrib,
            },
            user=user,
            api_key=api_key,
        )
        return True

    def callback(self, callback, recursive=False, *args, **kwargs):
        """Invoke callbacks of attached add-ons and collect messages.

        :param str callback: Name of callback method to invoke
        :param bool recursive: Apply callback recursively over nodes
        :return list: List of callback messages

        """
        messages = []

        for addon in self.get_addons():
            method = getattr(addon, callback)
            message = method(self, *args, **kwargs)
            if message:
                messages.append(message)

        if recursive:
            for child in self.nodes:
                messages.extend(
                    child.callback(
                        callback, recursive, *args, **kwargs
                    )
                )

        return messages

    def remove_contributor(self, contributor, user=None, api_key=None, log=True):
        """Remove a contributor from this node.

        :param contributor: User object, the contributor to be removed
        :param user: User object, the user who is removing the contributor.
        :param api_key: ApiKey object

        """
        if not user._primary_key == contributor._id:

            self.contributors.remove(contributor._id)
            self.contributor_list[:] = [d for d in self.contributor_list if d.get('id') != contributor._id]
            self.save()
            removed_user = get_user(contributor._id)

            # After remove callback
            for addon in self.get_addons():
                message = addon.after_remove_contributor(self, removed_user)
                if message:
                    status.push_status_message(message)

            if log:
                self.add_log(
                    action=NodeLog.CONTRIB_REMOVED,
                    params={
                        'project': self.parent_id,
                        'node': self._primary_key,
                        'contributor': removed_user._primary_key,
                    },
                    user=user,
                    api_key=api_key,
                )
            return True
        else:
            return False

    def add_contributor(self, contributor, user=None, log=True, api_key=None, save=False):
        """Add a contributor to the project.

        :param User contributor: The contributor to be added
        :param User user: The user who added the contributor or None.
        :param NodeLog log: Add log to self
        :param ApiKey api_key: API key used to add contributors
        :param bool save: Save after adding contributor
        :return bool: Whether contributor was added

        """
        MAX_RECENT_LENGTH = 15

        # If user is merged into another account, use master account
        contrib_to_add = contributor.merged_by if contributor.is_merged else contributor
        if contrib_to_add._primary_key not in self.contributors:
            self.contributors.append(contrib_to_add)
            self.contributor_list.append({'id': contrib_to_add._primary_key})

            # Add contributor to recently added list for user
            if user is not None:
                if contrib_to_add in user.recently_added:
                    user.recently_added.remove(contrib_to_add)
                user.recently_added.insert(0, contrib_to_add)
                while len(user.recently_added) > MAX_RECENT_LENGTH:
                    user.recently_added.pop()

            if log:
                self.add_log(
                    action=NodeLog.CONTRIB_ADDED,
                    params={
                        'project': self.parent_id,
                        'node': self._primary_key,
                        'contributors': [contrib_to_add._primary_key],
                    },
                    user=user,
                    api_key=api_key,
                    save=save,
                )
            if save:
                self.save()
            return True
        else:
            return False

    def add_contributors(self, contributors, user=None, log=True, api_key=None, save=False):
        """Add multiple contributors

        :param contributors: A list of User objects to add as contributors.
        :param user: A User object, the user who added the contributors.
        :param log: Add log to self
        :param api_key: API key used to add contributors
        :param save: Save after adding contributor

        """
        for contrib in contributors:
            self.add_contributor(contributor=contrib, user=user, log=False, save=False)
        if log:
            self.add_log(
                action=NodeLog.CONTRIB_ADDED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'contributors': [c._id for c in contributors],
                },
                user=user,
                api_key=api_key,
                save=save,
            )
        if save:
            self.save()

    def add_nonregistered_contributor(self, name, email, user, api_key=None, save=False):
        """Add a non-registered contributor to the project.

        :param name: A string, the full name of the person.
        :param email: A string, the email address of the person.
        :param user: A User object, the user who added the person.

        """
        self.contributor_list.append({'nr_name': name, 'nr_email': email})
        self.add_log(
            action=NodeLog.CONTRIB_ADDED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'contributors': [{"nr_name": name, "nr_email": email}],
            },
            user=user,
            api_key=api_key
        )
        if save:
            self.save()

    def set_permissions(self, permissions, user=None, api_key=None):
        """Set the permissions for this node.

        :param permissions: A string, either 'public' or 'private'
        :param user: A User object, the user who set the permissions
        :param api_key: API key used to change permissions

        """
        if permissions == 'public' and not self.is_public:
            self.is_public = True
            # If the node doesn't have a piwik site, make one.
            if settings.PIWIK_HOST:
                piwik.update_node(self)
        elif permissions == 'private' and self.is_public:
            self.is_public = False
        else:
            return False

        # After set permissions callback
        for addon in self.get_addons():
            message = addon.after_set_permissions(self, permissions)
            if message:
                status.push_status_message(message)

        action = NodeLog.MADE_PUBLIC if permissions == 'public' else NodeLog.MADE_PRIVATE
        self.add_log(
            action=action,
            params={
                'project':self.parent_id,
                'node':self._primary_key,
            },
            user=user,
            api_key=api_key
        )
        return True

    # TODO: Move to wiki add-on
    def get_wiki_page(self, page, version=None):
        from website.addons.wiki.model import NodeWikiPage

        page = urllib.unquote_plus(page)
        page = to_mongo(page)

        page = str(page).lower()
        if version:
            try:
                version = int(version)
            except:
                return None

            if not page in self.wiki_pages_versions:
                return None

            if version > len(self.wiki_pages_versions[page]):
                return None
            else:
                return NodeWikiPage.load(self.wiki_pages_versions[page][version-1])

        if page in self.wiki_pages_current:
            pw = NodeWikiPage.load(self.wiki_pages_current[page])
        else:
            pw = None

        return pw

    # TODO: Move to wiki add-on
    def update_node_wiki(self, page, content, user, api_key=None):
        """Update the node's wiki page with new content.

        :param page: A string, the page's name, e.g. ``"home"``.
        :param content: A string, the posted content.
        :param user: A `User` object.
        :param api_key: A string, the api key. Can be ``None``.

        """
        from website.addons.wiki.model import NodeWikiPage

        temp_page = page

        page = urllib.unquote_plus(page)
        page = to_mongo(page)
        page = str(page).lower()

        if page not in self.wiki_pages_current:
            version = 1
        else:
            current = NodeWikiPage.load(self.wiki_pages_current[page])
            current.is_current = False
            version = current.version + 1
            current.save()

        v = NodeWikiPage(
            page_name=temp_page,
            version=version,
            user=user,
            is_current=True,
            node=self,
            content=content
        )
        v.save()

        if page not in self.wiki_pages_versions:
            self.wiki_pages_versions[page] = []
        self.wiki_pages_versions[page].append(v._primary_key)
        self.wiki_pages_current[page] = v._primary_key

        self.add_log(
            action=NodeLog.WIKI_UPDATED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'page': v.page_name,
                'version': v.version,
            },
            user=user,
            api_key=api_key,
            log_date=v.date
        )

    def get_stats(self, detailed=False):
        if detailed:
            raise NotImplementedError(
                'Detailed stats exist, but are not yet implemented.'
            )
        else:
            return get_basic_counters('node:%s' % self._primary_key)

    def serialize(self):
        # TODO: incomplete implementation
        return {
            'id': str(self._primary_key),
            'category': self.project_or_component,
            'url': self.url,
            'title': self.title,
            'api_url': self.api_url,
            'is_public': self.is_public
        }


class WatchConfig(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    node = fields.ForeignField('Node', backref='watched')
    digest = fields.BooleanField(default=False)
    immediate = fields.BooleanField(default=False)
