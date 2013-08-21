
from framework import MongoObject
from framework.mongo import MongoCollectionStorage
from bson import ObjectId

from pymongo import MongoClient
db = MongoClient('mongodb://localhost:20771')['osf20120530']

class Keyword(MongoObject):
    schema = {
        '_id':{},
        'type':{'type':lambda: dict()},
    }
    _doc = {
        'name':'keyword',
        'version':1,
    }

Keyword.setStorage(MongoCollectionStorage(db, 'keyword'))

class User(MongoObject):
    schema = {
        '_id':{},
        "username":{},
        "password":{},
        "fullname":{},
        "is_registered":{},
        "is_claimed":{},
        "verification_key":{},
        "emails":{'type':[str]},
        "email_verifications":{'type':lambda: dict()},
        "aka":{'type':[str]},
        "date_registered":{'default':lambda: datetime.datetime.utcnow()},
        "keywords":{'type':[Keyword], 'backref':['keyworded']},
    }
    _doc = {
        'name':'user',
        'version':1,
    }

User.setStorage(MongoCollectionStorage(db, 'user'))

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