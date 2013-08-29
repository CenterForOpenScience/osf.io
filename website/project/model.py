from framework.mongo import MongoCollectionStorage, MongoObject, ObjectId, db
from framework.auth import User, get_user
from framework.analytics import get_basic_counters, increment_user_activity_counters
from framework.search import Keyword, generate_keywords
from framework.git.exceptions import FileNotModified

from website import settings

from modularodm import StoredObject
from modularodm import fields
from modularodm import storage

import hashlib
import datetime
import markdown
from markdown.extensions import wikilinks
import calendar
import os
import copy
import pymongo
import scrubber
import unicodedata
from bson import ObjectId

from dulwich.repo import Repo
from dulwich.object_store import tree_lookup_path

import subprocess

def utc_datetime_to_timestamp(dt):
    return float(
        str(calendar.timegm(dt.utcnow().utctimetuple())) + '.' + str(dt.microsecond)
    )

def normalize_unicode(ustr):
    return unicodedata.normalize('NFKD', ustr)\
        .encode('ascii', 'ignore')

# class NodeLog(MongoObject):
class NodeLog(StoredObject):
    # schema = {
    #     '_id':{'type': ObjectId, 'default':lambda: ObjectId()},
    #     'user':{'type':User, 'backref':['created']},
    #     'action':{},
    #     'date':{'default':lambda: datetime.datetime.utcnow()},
    #     'params':{},
    # }
    # _doc = {
    #     'name':'nodelog',
    #     'version':1,
    # }

    _id = fields.ObjectIdField(primary=True, default=ObjectId)

    date = fields.DateTimeField(default=datetime.datetime.utcnow)#auto_now=True)
    action = fields.StringField()
    params = fields.DictionaryField()

    user = fields.ForeignField('user', backref='created')

# NodeLog.setStorage(MongoCollectionStorage(db, 'nodelog'))
NodeLog.set_storage(storage.MongoStorage(db, 'nodelog'))

# class NodeFile(MongoObject):
class NodeFile(StoredObject):
    # schema = {
    #     '_id':{'type': ObjectId, 'default':lambda: ObjectId()},
    #     "path":{},
    #     "filename":{},
    #     "md5":{},
    #     "sha":{},
    #     "size":{},
    #     "content_type":{},
    #     "uploader":{'type':User, 'backref':['uploads']},
    #     "is_public":{},
    #     "git_commit":{},
    #     "is_deleted":{},
    #     "date_created":{'default':lambda: datetime.datetime.utcnow()},
    #     "date_modified":{'default':lambda: datetime.datetime.utcnow()},
    #     "date_uploaded":{'default':lambda: datetime.datetime.utcnow()},
    #     "_terms":{'type':[]},
    # }
    #
    # _doc = {
    #     'name':'nodefile',
    #     'version':1,
    # }

    _id = fields.ObjectIdField(primary=True, default=ObjectId)

    path = fields.StringField()
    filename = fields.StringField()
    md5 = fields.StringField()
    sha = fields.StringField()
    size = fields.IntegerField()
    content_type = fields.StringField()
    is_public = fields.BooleanField()
    git_commit = fields.StringField()
    is_deleted = fields.BooleanField()

    date_created = fields.DateTimeField(default=datetime.datetime.utcnow())#auto_now_add=True)
    date_modified = fields.DateTimeField(default=datetime.datetime.utcnow())#auto_now=True)
    date_uploaded = fields.DateTimeField(default=datetime.datetime.utcnow())

    uploader = fields.ForeignField('user', backref='uploads')

# NodeFile.setStorage(MongoCollectionStorage(db, 'nodefile'))
NodeFile.set_storage(storage.MongoStorage(db, 'nodefile'))

# class Tag(MongoObject):
class Tag(StoredObject):

    schema = {
        '_id':{},
        'count_public':{"default":0},
        'count_total':{"default":0},
    }
    _doc = {
        'name':'tag',
        'version':1,
    }

    _id = fields.StringField(primary=True)
    count_public = fields.IntegerField(default=0)
    count_total = fields.IntegerField(default=0)

# Tag.setStorage(MongoCollectionStorage(db, 'tag'))
Tag.set_storage(storage.MongoStorage(db, 'tag'))

# class Node(MongoObject):
class Node(StoredObject):
    # schema = {
    #     '_id':{},
    #     'is_deleted':{"default":False},
    #     'deleted_date':{},
    #     'is_registration':{"default":False},
    #     "is_fork":{"default":False},
    #     "title":{},
    #     "description":{},
    #     "category":{},
    #     "creator":{'type':User, 'backref':['created']},
    #     "contributors":{'type':[User], 'backref':['contributed']},
    #     "contributor_list":{"type": [], 'default':lambda: list()}, # {id, nr_name, nr_email}
    #     "users_watching_node":{'type':[User], 'backref':['watched']},
    #     "is_public":{},
    #     "date_created":{'default':lambda: datetime.datetime.utcnow()},
    #     "_terms":{'type':[]},
    #     "files_current": {"default":lambda: dict()},
    #     "files_versions": {"default":lambda: dict()},
    #     "wiki_pages_current":{"default":lambda: dict()},
    #     "wiki_pages_versions":{"default":lambda: dict()},
    #     "logs":{'type':[NodeLog], 'backref':['logged']}, # {date: { user, action, type, ref}} or parent
    #     "tags":{'type':[Tag], 'backref':['tagged']},
    #     "registered_date":{},
    #     "forked_date":{},
    #     "registered_meta":{"default":lambda: dict()},
    #     "_terms":{'type':[]},
    # }
    #
    # _doc = {
    #     'name':'node',
    #     'version':1,
    # }

    _id = fields.StringField(primary=True)

    date_created = fields.DateTimeField(default=datetime.datetime.utcnow)
    is_public = fields.BooleanField()

    is_deleted = fields.BooleanField(default=False)
    deleted_date = fields.DateTimeField()

    is_registration = fields.BooleanField(default=False)
    registered_date = fields.DateTimeField()

    is_fork = fields.BooleanField(default=False)
    forked_date = fields.DateTimeField()

    title = fields.StringField()
    description = fields.StringField()
    category = fields.StringField()

    _terms = fields.DictionaryField(list=True)
    registration_list = fields.StringField(list=True)
    fork_list = fields.StringField(list=True)
    registered_meta = fields.DictionaryField()

    files_current = fields.DictionaryField()
    files_versions = fields.DictionaryField()
    wiki_pages_current = fields.DictionaryField()
    wiki_pages_versions = fields.DictionaryField()

    creator = fields.ForeignField('user', backref='created')
    contributors = fields.ForeignField('user', list=True, backref='contributed')
    contributor_list = fields.DictionaryField(list=True)
    users_watching_node = fields.ForeignField('user', list=True, backref='watched')

    logs = fields.ForeignField('nodelog', list=True, backref='logged')
    tags = fields.ForeignField('tag', list=True, backref='tagged')

    nodes = fields.ForeignField('node', list=True, backref='parent')
    forked_from = fields.ForeignField('node', backref='forked')
    registered_from = fields.ForeignField('node', backref='registrations')

    _meta = {'optimistic' : True}

    def remove_node(self, user, date=None):
        if not date:
            date = datetime.datetime.utcnow()

        node_objects = []
 
        if self.nodes and len(self.nodes) > 0:
            node_objects = self.nodes

        #if self.node_registations and len(self.node_registrations) > 0:
        #    return False

        for node in node_objects:
            #if not node.user_is_contributor(user):
            #    return False
            
            if not node.category == 'project':
                if not node.remove_node(user, date=date):
                    return False

        # Remove self from parent registration list
        if self.is_registration:
            registered_from = Node.load(self.registered_from)
            try:
                registered_from.registration_list.remove(self._primary_key)
                registered_from.save()
            except ValueError:
                pass

        # Remove self from parent fork list
        if self.is_fork:
            forked_from = Node.load(self.forked_from)
            try:
                forked_from.fork_list.remove(self._primary_key)
                forked_from.save()
            except ValueError:
                pass

        self.is_deleted = True
        self.deleted_date = date
        self.save()

        return True

    def generate_keywords(self, save=True):
        source = []
        keywords = []
        source.append(self.title)
        for k,v in self.wiki_pages_current.items():
            page = NodeWikiPage.load(v)
            source.append(page.content)
        for t in self.tags:
            source.append(t._id)
        self._terms = []
        # TODO force tags, add users, files
        self._terms = generate_keywords(source)
        if save:
            self.save()
        return 

    def fork_node(self, user, title='Fork of '):
        if not (self.is_contributor(user) or self.is_public):
            return

        folder_old = os.path.join(settings.uploads_path, self._primary_key)

        when = datetime.datetime.utcnow()

        original = self.load(self._primary_key)
        forked = original.clone()

        # forked.save()
        forked._optimistic_insert()

        if os.path.exists(folder_old):
            folder_new = os.path.join(settings.uploads_path, forked._primary_key)
            Repo(folder_old).clone(folder_new)

        forked.nodes = []

        for i, node_contained in enumerate(original.nodes):
            forked_node = node_contained.fork_node(user, title='')
            if forked_node is not None:
                forked.nodes.append(forked_node)

        forked.title = title + forked.title
        forked.is_fork = True
        forked.forked_date = when
        forked.forked_from = original
        forked.is_public = False

        forked.contributors = []
        forked.contributor_list = []
        forked.add_contributor(user, log=False, save=False)
        forked.save()

        forked.add_log('node_forked',
            params={
                'project':original.node__parent[0]._primary_key if original.node__parent else None,
                'node':original._primary_key,
                'registration':forked._primary_key,
            }, 
            user=user,
            log_date=when
        )

        original.fork_list.append(forked._primary_key)
        original.save()

        return forked#self

    def register_node(self, user, template, data):
        folder_old = os.path.join(settings.uploads_path, self._primary_key)

        when = datetime.datetime.utcnow()

        original = self.load(self._primary_key)
        registered = original.clone()
        registered._optimistic_insert()

        if os.path.exists(folder_old):
            folder_new = os.path.join(settings.uploads_path, registered._primary_key)
            Repo(folder_old).clone(folder_new)

        self.nodes = []
        # while len(self.nodes) > 0:
        #     self.nodes.pop()

        for i, node_contained in enumerate(original.nodes):
            original_node = self.load(node_contained._primary_key)
            folder_old = os.path.join(settings.uploads_path, node_contained._primary_key)

            node_contained._optimistic_insert()

            if os.path.exists(folder_old):
                folder_new = os.path.join(settings.uploads_path, node_contained._primary_key)
                Repo(folder_old).clone(folder_new)

            node_contained.is_registration = True
            node_contained.registered_date = when
            node_contained.registered_from = original_node
            if not node_contained.registered_meta:
                node_contained.registered_meta = {}
            node_contained.registered_meta[template] = data
            node_contained.save()

            registered.nodes.append(node_contained)

        registered.is_registration = True
        registered.registered_date = when
        registered.registered_from = original
        if not registered.registered_meta:
            registered.registered_meta = {}
        registered.registered_meta[template] = data
        registered.save()

        original.add_log('project_registered', 
            params={
                'project':original.node__parent._primary_key if original.node__parent else None,
                'node':original._primary_key,
                'registration':registered._primary_key,
            }, 
            user=user,
            log_date=when
        )
        original.registration_list.append(registered._id)
        original.save()

        return registered

    def remove_tag(self, tag, user):
        if tag in self.tags:
            new_tag = Tag.load(tag)
            self.tags.remove(tag)
            self.save()
            self.add_log('tag_removed', {
                'project':self.node__parent._primary_key if self.node__parent else None,
                'node':self._primary_key,
                'tag':tag,
            }, user)

    def add_tag(self, tag, user):
        if tag not in self.tags:
            new_tag = Tag.load(tag)
            if not new_tag:
                new_tag = Tag(_id=tag)
            new_tag.count_total+=1
            if self.is_public:
                new_tag.count_public+=1
            new_tag.save()
            self.tags.append(new_tag)
            self.save()
            self.add_log('tag_added', {
                'project':self.node__parent._primary_key if self.node__parent else None,
                'node':self._primary_key,
                'tag':tag,
            }, user)

    def get_file(self, path, version=None):
        if not version == None:
            folder_name = os.path.join(settings.uploads_path, self._primary_key)
            if os.path.exists(os.path.join(folder_name, ".git")):
                file_object =  NodeFile.load(self.files_versions[path.replace('.', '_')][version])
                repo = Repo(folder_name)
                tree = repo.commit(file_object.git_commit).tree
                (mode,sha) = tree_lookup_path(repo.get_object,tree,path)
                return repo[sha].data, file_object.content_type
        return None,None

    def get_file_object(self, path, version=None):
        if version is not None:
            directory = os.path.join(settings.uploads_path, self._primary_key)
            if os.path.exists(os.path.join(directory, '.git')):
                return NodeFile.load(self.files_versions[path.replace('.', '_')][version])
            # TODO: Raise exception here
        return None, None # TODO: Raise exception here

    def remove_file(self, user, path):
        '''Removes a file from the filesystem, NodeFile collection, and does a git delete ('git rm <file>')

        :param user:
        :param path:

        :return: True on success, False on failure
        '''

        #FIXME: encoding the filename this way is flawed. For instance - foo.bar resolves to the same string as foo_bar.
        file_name_key = path.replace('.', '_')

        repo_path = os.path.join(settings.uploads_path, self._primary_key)

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
            committer = u'{fullname} <user-{id}@openscienceframework.org>'.format(
                fullname=user.fullname,
                id=user._primary_key
            )
            ascii_committer = normalize_unicode(committer)
            commit_id = repo.do_commit(message, ascii_committer)

        except subprocess.CalledProcessError:
            return False

        date_modified = datetime.datetime.now()

        if file_name_key in self.files_current:
            nf = NodeFile.load(self.files_current[file_name_key])
            nf.is_deleted = True
            nf.date_modified = date_modified
            nf.save()
            self.files_current.pop(file_name_key, None)

        if file_name_key in self.files_versions:
            for i in self.files_versions[file_name_key]:
                nf = NodeFile.load(i)
                nf.is_deleted = True
                nf.date_modified = date_modified
                nf.save()
            self.files_versions.pop(file_name_key)

        self.add_log('file_removed', {
                'project':self.node__parent._primary_key if self.node__parent else None,
                'node':self._primary_key,
                'path':path
            }, user, log_date=date_modified)

        self.save()
        return True

    def add_file(self, user, file_name, content, size, content_type):
        """
        Instantiates a new NodeFile object, and adds it to the current Node as
        necessary.
        """
        # TODO: Reading the whole file into memory is not scalable. Fix this.

        # This node's folder
        folder_name = os.path.join(settings.uploads_path, self._primary_key)

        # TODO: This should be part of the build phase, not here.
        # verify the upload root exists
        if not os.path.isdir(settings.uploads_path):
            os.mkdir(settings.uploads_path)

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
        committer = u'{name} <user-{id}@openscienceframework.org>'.format(
            name=user.fullname,
            id=user._primary_key,
        )
        ascii_committer = normalize_unicode(committer)

        commit_id = repo.do_commit(
            message=unicode(file_name +
                            (' added' if file_is_new else ' updated')),
            committer=ascii_committer,
        )

        # Deal with creating a NodeFile in the database
        node_file = NodeFile()
        node_file.path = file_name
        node_file.filename = file_name
        node_file.size = size
        node_file.is_public = self.is_public
        node_file.uploader = user
        node_file.git_commit = commit_id
        node_file.content_type = content_type
        node_file.is_deleted = False
        node_file.save()

        # Add references to the NodeFile to the Node object
        file_name_key = file_name.replace('.', '_')

        # Reference the current file version
        self.files_current[file_name_key] = node_file._primary_key

        # Create a version history if necessary
        if not file_name_key in self.files_versions:
            self.files_versions[file_name_key] = []

        # Add reference to the version history
        self.files_versions[file_name_key].append(node_file._primary_key)

        # Save the Node
        self.save()

        if file_is_new:
            self.add_log('file_added', {
                'project': self.node__parent._primary_key if self.node__parent else None,
                'node': self._primary_key,
                'path': node_file.path,
                'version': len(self.files_versions)
            }, user, log_date=node_file.date_uploaded)
        else:
            self.add_log('file_updated', {
                'project': self.node__parent._primary_key if self.node__parent else None,
                'node': self._primary_key,
                'path': node_file.path,
                'version': len(self.files_versions)
            }, user, log_date=node_file.date_uploaded)

        return node_file
    
    def add_log(self, action, params, user, log_date = None):
        log = NodeLog()
        log.action=action
        log.user=user
        if log_date:
            log.date=log_date
        log.params=params
        log.save()
        self.logs.append(log)
        self.save()
        increment_user_activity_counters(user._primary_key, action, log.date)
        if self.node__parent:
            parent = self.node__parent[0]
            parent.logs.append(log)
            parent.save()

    def url(self):
        if self.category == 'project':
            return '/project/' + self._primary_key
        else:
            if self.node__parent and self.node__parent[0].category == 'project':
                return '/project/' + self.node__parent[0]._primary_key + '/node/' + self._primary_key # todo just get this directly


    def is_contributor(self, user):
        if user:
            if str(user._id) in self.contributors:
                return True
        return False
    
    def remove_nonregistered_contributor(self, user, name, hash):
        for d in self.contributor_list:
            if d.get('nr_name') == name and hashlib.md5(d.get('nr_email')).hexdigest() == hash:
                email = d.get('nr_email')
        self.contributor_list[:] = [d for d in self.contributor_list if not (d.get('nr_email') == email)]
        self.save()
        self.add_log('remove_contributor', 
            params={
                'project':self.node__parent._primary_key if self.node__parent else None,
                'node':self._primary_key,
                'contributor':{"nr_name":name, "nr_email":email},
            }, 
            user=user,
        )
        return True

    def remove_contributor(self, user, user_id_to_be_removed):
        if not user._primary_key == user_id_to_be_removed:
            self.contributors.remove(user_id_to_be_removed)
            self.contributor_list[:] = [d for d in self.contributor_list if d.get('id') != user_id_to_be_removed]
            self.save()
            # # todo allow backref mechanism to handle this; not implemented
            removed_user = get_user(user_id_to_be_removed)
            # removed_user._b_node_contributed.remove(self._primary_key)
            # removed_user.save()

            self.add_log('remove_contributor', 
                params={
                    'project':self.node__parent[0]._primary_key if self.node__parent else None,
                    'node':self._primary_key,
                    'contributor':removed_user._primary_key,
                }, 
                user=user,
            )
            return True
        else:
            return False

    def add_contributor(self, user, log=True, save=False):
        if user._primary_key not in self.contributors:
            self.contributors.append(user)
            self.contributor_list.append({'id':user._primary_key})
            if save:
                self.save()
            if log:
                pass
            #self.add_log('contributor_added', 
            #    params={
            #        'project':self.node_parent._primary_key if self.node_parent else None,
            #        'node':self._primary_key,
            #        'contributors':[user._primary_key],
            #    }, 
            #    user=user,
            #)

    def makePublic(self, user):
        if not self.is_public:
            self.is_public = True
            self.save()
            self.add_log('made_public', 
                params={
                    'project':self.node__parent._primary_key if self.node__parent else None,
                    'node':self._primary_key,
                }, 
                user=user,
            )
        return True

    def makePrivate(self, user):
        if self.is_public:
            self.is_public = False
            self.save()
            self.add_log('made_private',
                params={
                    'project':self.node__parent._primary_key if self.node__parent else None,
                    'node':self._primary_key,
                },
                user=user,
            )
        return True

    def get_wiki_page(self, page, version=None):
        # len(wiki_pages_versions) == 1, version 1
        # len() == 2, version 1, 2

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

    def updateNodeWikiPage(self, page, content, user):
        page = str(page).lower()

        if page not in self.wiki_pages_current:
            version = 1
        else:
            current = NodeWikiPage.load(self.wiki_pages_current[page])
            current.is_current = False
            version = current.version + 1
            current.save()

        v = NodeWikiPage()
        v.page_name = page
        v.version = version
        v.user = user
        v.is_current = True
        v.node = self
        v.content = content
        v.save()

        if page not in self.wiki_pages_versions:
            self.wiki_pages_versions[page] = []
        self.wiki_pages_versions[page].append(v._primary_key)
        self.wiki_pages_current[page] = v._primary_key

        self.generate_keywords(save=False)

        self.save()

        self.add_log('wiki_updated', 
            params={
                'project':self.node__parent._primary_key if self.node__parent else None,
                'node':self._primary_key,
                'page':v.page_name,
                'version': v.version,
            }, 
            user=user,
            log_date=v.date
        )

    def get_stats(self, detailed=False):
        if detailed:
            raise NotImplementedError(
                'Detailed stats exist, but are not yet implemented.'
            )
        else:
            return get_basic_counters('node:%s' % self._primary_key)

# Node.schema['forked_from'] = {'type':Node, 'backref':['forked']}
# Node.schema['nodes'] = {'type':[Node], 'backref':'parent'}
# Node.schema['registered_from'] = {'type':Node, 'backref':['registrations']}

# Node.setStorage(MongoCollectionStorage(db, 'node'))
Node.set_storage(storage.MongoStorage(db, 'node'))

# class NodeWikiPage(MongoObject):
class NodeWikiPage(StoredObject):
    # schema = {
    #     '_id':{'type': ObjectId, 'default':lambda: ObjectId()},
    #     'page_name':{},
    #     'version':{},
    #     'user':{'type':User},
    #     'date':{'default':lambda: datetime.datetime.utcnow()},
    #     'is_current':{},
    #     'node':{'type':Node}, # parent
    #     'content':{},
    # }
    # _doc = {
    #     'name':'nodewikipage',
    #     'version':1,
    # }

    _id = fields.ObjectIdField(primary=True, default=ObjectId)
    page_name = fields.StringField()
    version = fields.IntegerField()
    date = fields.DateTimeField()#auto_now_add=True)
    is_current = fields.BooleanField()
    content = fields.StringField()

    user = fields.ForeignField('user')
    node = fields.ForeignField('node')

    _meta = {'optimistic' : True}

    @property
    def html(self):
        """The cleaned HTML of the page"""
        wiki_scrubber = scrubber.Scrubber(autolink=False)

        html_output = markdown.markdown(
            self.content,
            extensions=[
                wikilinks.WikiLinkExtension(
                    configs=[('base_url', ''), ('end_url', '')]
                )
            ]
        )

        return wiki_scrubber.scrub(html_output)

# NodeWikiPage.setStorage(MongoCollectionStorage(db, 'nodewikipage'))
NodeWikiPage.set_storage(storage.MongoStorage(db, 'nodewikipage'))