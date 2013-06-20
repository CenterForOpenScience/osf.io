from Framework.Mongo import *
from Framework.Auth import *
from Framework.Debug import *
from Framework.Analytics import *
from Framework.Search import Keyword, generateKeywords

import Site.Settings
from Framework.Mongo import db as mongodb

import hashlib
import datetime
import markdown
import calendar
import os
import copy
import pymongo

from dulwich.repo import Repo
from dulwich.object_store import tree_lookup_path

import subprocess

def utc_datetime_to_timestamp(dt):
    return float(
        str(calendar.timegm(dt.utcnow().utctimetuple())) + '.' + str(dt.microsecond)
    )

class NodeLog(MongoObject):
    schema = {
        '_id':{'type': ObjectId, 'default':lambda: ObjectId()},
        'user':{'type':User, 'backref':['created']},
        'action':{},
        'date':{'default':lambda: datetime.datetime.utcnow()},
        'params':{},
    }
    _doc = {
        'name':'nodelog',
        'version':1,
    }

NodeLog.setStorage(MongoCollectionStorage(db, 'nodelog'))

class NodeFile(MongoObject):
    schema = {
        '_id':{'type': ObjectId, 'default':lambda: ObjectId()},
        "path":{},
        "filename":{},
        "md5":{},
        "sha":{},
        "size":{},
        "content_type":{},
        "uploader":{'type':User, 'backref':['uploads']},
        "is_public":{},
        "git_commit":{},
        "is_deleted":{},
        "date_created":{'default':lambda: datetime.datetime.utcnow()},
        "date_modified":{'default':lambda: datetime.datetime.utcnow()},
        "date_uploaded":{'default':lambda: datetime.datetime.utcnow()},
        "_terms":{'type':[]},
    }
    
    _doc = {
        'name':'nodefile',
        'version':1,
    }

NodeFile.setStorage(MongoCollectionStorage(db, 'nodefile'))

class Tag(MongoObject):
    schema = {
        '_id':{},
        'count_public':{"default":0},
        'count_total':{"default":0},
    }
    _doc = {
        'name':'tag',
        'version':1,
    }

Tag.setStorage(MongoCollectionStorage(db, 'tag'))

class Node(MongoObject):
    schema = {
        '_id':{},
        'is_deleted':{"default":False},
        'deleted_date':{},
        'is_registration':{"default":False},
        "is_fork":{"default":False},
        "title":{},
        "description":{},
        "category":{},
        "creator":{'type':User, 'backref':['created']},
        "contributors":{'type':[User], 'backref':['contributed']},
        "contributor_list":{"type": [], 'default':lambda: list()}, # {id, nr_name, nr_email}
        "users_watching_node":{'type':[User], 'backref':['watched']},
        "is_public":{},
        "date_created":{'default':lambda: datetime.datetime.utcnow()},
        "_terms":{'type':[]},
        "files_current": {"default":lambda: dict()},
        "files_versions": {"default":lambda: dict()},
        "wiki_pages_current":{"default":lambda: dict()},
        "wiki_pages_versions":{"default":lambda: dict()},
        "logs":{'type':[NodeLog], 'backref':['logged']}, # {date: { user, action, type, ref}} or parent
        "tags":{'type':[Tag], 'backref':['tagged']},
        "registered_date":{},
        "forked_date":{},
        "registered_meta":{"default":lambda: dict()},
        "_terms":{'type':[]},
    }
    
    _doc = {
        'name':'node',
        'version':1,
    }

    def remove_node(self, user, date=None):
        if not date:
            date = datetime.datetime.utcnow()

        node_objects = []
 
        if self.nodes and len(self.nodes) > 0:
            node_objects = self.nodes.objects()

        #if self.node_registations and len(self.node_registrations) > 0:
        #    return False

        for node in node_objects:
            #if not node.is_contributor(user):
            #    return False
            
            if not node.category == 'project':
                if not node.remove_node(user, date=date):
                    return False

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
            source.append(t)
        self._terms = []
        # TODO force tags, add users, files
        self._terms = generateKeywords(source)
        if save:
            self.save()
        return 

    def fork_node(self, user, title='Fork of '):
        if not (self.is_contributor(user) or self.is_public):
            return

        folder_old = os.path.join(Site.Settings.uploads_path, self.id)

        when = datetime.datetime.utcnow()

        original = self.load(self.id)
        self.optimistic_insert()

        if os.path.exists(folder_old):
            folder_new = os.path.join(Site.Settings.uploads_path, self.id)
            Repo(folder_old).clone(folder_new)
        
        # TODO empty lists
        while len(self.nodes) > 0:
            self.nodes.pop()

        for i, node_contained in enumerate(original.nodes.objects()):
            self.nodes.append(node_contained.fork_node(user, title=''))

        self.title = title + self.title
        self.is_fork = True
        self.forked_date = when
        self.forked_from = original
        self.is_public = False
        if self.node_forked:
            while len(self.node_forked) > 0:
                self.node_forked.pop()

        # TODO empty lists
        while len(self.contributors) > 0:
            self.contributors.pop()
        while len(self.contributor_list) > 0:
            self.contributor_list.pop()
        self.add_contributor(user, log=False, save=False)
        self.save()

        self.add_log('node_forked', 
            params={
                'project':original.node_parent.id if original.node_parent else None,
                'node':original.id,
                'registration':self.id,
            }, 
            user=user,
            log_date=when
        )

        return self

    def register_node(self, user, template, data):
        folder_old = os.path.join(Site.Settings.uploads_path, self.id)

        when = datetime.datetime.utcnow()

        original = self.load(self.id)
        self.optimistic_insert()

        if os.path.exists(folder_old):
            folder_new = os.path.join(Site.Settings.uploads_path, self.id)
            Repo(folder_old).clone(folder_new)
        
        while len(self.nodes) > 0:
            self.nodes.pop()

        for i, node_contained in enumerate(original.nodes.objects()):
            original_node = self.load(node_contained.id)
            folder_old = os.path.join(Site.Settings.uploads_path, node_contained.id)

            node_contained.optimistic_insert()

            if os.path.exists(folder_old):
                folder_new = os.path.join(Site.Settings.uploads_path, node_contained.id)
                Repo(folder_old).clone(folder_new)

            node_contained.is_registration = True
            node_contained.registered_date = when
            node_contained.registered_from = original_node
            if not node_contained.registered_meta:
                node_contained.registered_meta = {}
            node_contained.registered_meta[template] = data
            node_contained.save()

            self.nodes.append(node_contained)

        self.is_registration = True
        self.registered_date = when
        self.registered_from = original
        if not self.registered_meta:
            self.registered_meta = {}
        self.registered_meta[template] = data
        self.save()

        original.add_log('project_registered', 
            params={
                'project':original.node_parent.id if original.node_parent else None,
                'node':original.id,
                'registration':self.id,
            }, 
            user=user,
            log_date=when
        )

        return self

    def remove_tag(self, tag, user):
        if tag in self.tags:
            new_tag = Tag.load(tag)
            new_tag._b_node_tagged.remove(self.id)
            new_tag.save()
            self.tags.remove(tag)
            self.save()
            self.add_log('tag_removed', {
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
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
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
                'tag':tag,
            }, user)


    def get_file(self, path, version=None):
        if not version == None:
            folder_name = os.path.join(Site.Settings.uploads_path, self.id)
            if os.path.exists(os.path.join(folder_name, ".git")):
                file_object =  NodeFile.load(self.files_versions[path.replace('.', '_')][version])
                repo = Repo(folder_name)
                tree = repo.commit(file_object.git_commit).tree
                (mode,sha) = tree_lookup_path(repo.get_object,tree,path)
                return repo[sha].data, file_object.content_type
        return None,None

    def remove_file(self, user, path):
        '''Removes a file from the filesystem, NodeFile collection, and does a git delete ('git rm <file>')

        :param user:
        :param path:

        :return: True on success, False on failure
        '''

        #FIXME: encoding the filename this way is flawed. For instance - foo.bar resolves to the same string as foo_bar.
        file_name_key = path.replace('.', '_')

        repo_path = os.path.join(Site.Settings.uploads_path, self.id)

        # TODO make sure it all works, otherwise rollback as needed
        # Do a git delete, which also removes from working filesystem.
        try:
            subprocess.check_output(
                ['git', 'rm', path],
                cwd=repo_path,
                shell=False
            )

            repo = Repo(repo_path)

            commit_id = repo.do_commit(
                '%s deleted' % path,
                '%s <user-%s@openscienceframework.org>' % (user.fullname, user.id)
            )

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
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
                'path':path
            }, user, log_date=date_modified)

        self.save()
        return True

    def add_file(self, user, file_name, content, size, content_type):
        folder_name = os.path.join(Site.Settings.uploads_path, self.id)

        # TODO: This should be part of the build phase, not here.
        # verify the upload root exists
        if not os.path.isdir(Site.Settings.uploads_path):
            os.mkdir(Site.Settings.uploads_path)

        if os.path.exists(folder_name):
            if os.path.exists(os.path.join(folder_name, ".git")):
                repo = Repo(folder_name)
            else:
                repo = Repo.init(folder_name)
        else:
            os.mkdir(folder_name)
            repo = Repo.init(folder_name)

        if os.path.exists(os.path.join(folder_name, file_name)):
            file_new = True
        else:
            file_new = False

        with open(os.path.join(folder_name, file_name), 'wb') as f:
            f.write(content)

        repo.stage([file_name])

        if file_new:
            commit_message = file_name + ' added'
        else:
            commit_message = file_name + ' updated'

        committer = user.fullname + ' <user-' + str(user.id) + '@openscienceframework.org>'
        loggerDebug('add_file', committer)
        commit_id = repo.do_commit(commit_message, committer)

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

        file_name_key = file_name.replace('.', '_')
        self.files_current[file_name_key] = node_file.id
        if not file_name_key in self.files_versions:
            self.files_versions[file_name_key] = []
        self.files_versions[file_name_key].append(node_file.id)
        self.save()

        if file_new:
            self.add_log('file_added', {
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
                'path':node_file.path,
                'version':len(self.files_versions)
            }, user, log_date=node_file.date_uploaded)
        else:
            self.add_log('file_updated', {
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
                'path':node_file.path,
                'version':len(self.files_versions)
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
        increment_user_activity_counters(user.id, action, log.date)
        if self.node_parent:
            parent = self.node_parent
            parent.logs.append(log)
            parent.save()

    def url(self):
        if self.category == 'project':
            return '/project/' + self.id
        else:
            if self.node_parent and self.node_parent.category == 'project':
                return '/project/' + self.node_parent.id + '/node/' + self.id # todo just get this directly


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
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
                'contributor':{"nr_name":name, "nr_email":email},
            }, 
            user=user,
        )
        return True

    def remove_contributor(self, user, user_id_to_be_removed):
        if not user.id == user_id_to_be_removed:
            self.contributors.remove(user_id_to_be_removed)
            self.contributor_list[:] = [d for d in self.contributor_list if d.get('id') != user_id_to_be_removed]
            self.save()
            # todo allow backref mechanism to handle this; not implemented
            removed_user = getUser(user_id_to_be_removed)
            removed_user._b_node_contributed.remove(self.id)
            removed_user.save()

            self.add_log('remove_contributor', 
                params={
                    'project':self.node_parent.id if self.node_parent else None,
                    'node':self.id,
                    'contributor':removed_user.id,
                }, 
                user=user,
            )
            return True
        else:
            return False

    def add_contributor(self, user, log=True, save=False):
        if user.id not in self.contributors:
            self.contributors.append(user)
            self.contributor_list.append({'id':user.id})
            if save:
                self.save()
            if log:
                pass
            #self.add_log('contributor_added', 
            #    params={
            #        'project':self.node_parent.id if self.node_parent else None,
            #        'node':self.id,
            #        'contributors':[user.id],
            #    }, 
            #    user=user,
            #)

    def makePublic(self, user):
        if not self.is_public:
            self.is_public = True
            self.save()
            self.add_log('made_public', 
                params={
                    'project':self.node_parent.id if self.node_parent else None,
                    'node':self.id,
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
                    'project':self.node_parent.id if self.node_parent else None,
                    'node':self.id,
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
        self.wiki_pages_versions[page].append(v.ref)
        self.wiki_pages_current[page] = v.ref

        self.generate_keywords(save=False)

        self.save()

        self.add_log('wiki_updated', 
            params={
                'project':self.node_parent.id if self.node_parent else None,
                'node':self.id,
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
            return getBasicCounters('node:%s' % self.id)

Node.schema['forked_from'] = {'type':Node, 'backref':['forked']}
Node.schema['nodes'] = {'type':[Node], 'backref':'parent'}
Node.schema['registered_from'] = {'type':Node, 'backref':['registrations']}

Node.setStorage(MongoCollectionStorage(db, 'node'))

class NodeWikiPage(MongoObject):
    schema = {
        '_id':{'type': ObjectId, 'default':lambda: ObjectId()},
        'page_name':{},
        'version':{},
        'user':{'type':User},
        'date':{'default':lambda: datetime.datetime.utcnow()},
        'is_current':{},
        'node':{'type':Node}, # parent
        'content':{},
    }
    _doc = {
        'name':'nodewikipage',
        'version':1,
    }

NodeWikiPage.setStorage(MongoCollectionStorage(db, 'nodewikipage'))