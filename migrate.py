"""
Migrate schemas from yORM to ODM. For the moment, copies data from the database
defined in website/settings.py to a database managed by a Mongo daemon running
on port 27017. Data are migrated to a database called "migrate".
"""

import pymongo
from bson import ObjectId
import logging
import pprint
import time

from modularodm import StoredObject
from modularodm import fields
from modularodm import storage
from modularodm.query.querydialect import DefaultQueryDialect as Q

from framework.search.model import Keyword
from framework.auth.model import User
from website.project.model import Tag
from website.project.model import NodeLog
from website.project.model import NodeFile
from website.project.model import Node
from website.project.model import NodeWikiPage

import schema_yorm

client = pymongo.MongoClient()
database = client['migrate']

# Schemas must be migrated in order to preserve relationships. This
# could be implemented using some kind of dependency tracking, but is
# done by hand for now.
migrate_order = [
    'Keyword',
    'User',
    'Tag',
    'NodeLog',
    'NodeFile',
    'Node',
    'NodeWikiPage',
]

# # Schema definitions
#
# class Keyword(StoredObject):
#
#     _id = fields.StringField(primary=True)
#     type = fields.DictionaryField()
#
# Keyword.set_storage(storage.MongoStorage(database, 'keyword'))
#
# class User(StoredObject):
#
#     _id = fields.StringField(primary=True)
#
#     username = fields.StringField()
#     password = fields.StringField()
#     fullname = fields.StringField()
#     is_registered = fields.BooleanField()
#     is_claimed = fields.BooleanField()
#     verification_key = fields.StringField()
#     emails = fields.StringField(list=True)
#     email_verifications = fields.DictionaryField()
#     aka = fields.StringField(list=True)
#     date_registered = fields.DateTimeField()#auto_now_add=True)
#
#     keywords = fields.ForeignField('keyword', list=True, backref='keyworded')
#
# User.set_storage(storage.MongoStorage(database, 'user'))
#
# class NodeLog(StoredObject):
#
#     _id = fields.ObjectIdField(primary=True)
#
#     date = fields.DateTimeField()#auto_now=True)
#     action = fields.StringField()
#     params = fields.DictionaryField()
#
#     user = fields.ForeignField('user', backref='created')
#
# NodeLog.set_storage(storage.MongoStorage(database, 'nodelog'))
#
# class NodeFile(StoredObject):
#
#     _id = fields.ObjectIdField(primary=True)
#
#     path = fields.StringField()
#     filename = fields.StringField()
#     md5 = fields.StringField()
#     sha = fields.StringField()
#     size = fields.IntegerField()
#     content_type = fields.StringField()
#     is_public = fields.BooleanField()
#     git_commit = fields.StringField()
#     is_deleted = fields.BooleanField()
#
#     date_created = fields.DateTimeField()#auto_now_add=True)
#     date_modified = fields.DateTimeField()#auto_now=True)
#     date_uploaded = fields.DateTimeField()
#
#     uploader = fields.ForeignField('user', backref='uploads')
#
# NodeFile.set_storage(storage.MongoStorage(database, 'nodefile'))
#
# class NodeWikiPage(StoredObject):
#
#     _id = fields.ObjectIdField(primary=True, default=ObjectId)
#     page_name = fields.StringField()
#     version = fields.IntegerField()
#     date = fields.DateTimeField()#auto_now_add=True)
#     is_current = fields.BooleanField()
#     content = fields.StringField()
#
#     user = fields.ForeignField('user')
#     node = fields.ForeignField('node')
#
# NodeWikiPage.set_storage(storage.MongoStorage(database, 'nodewikipage'))
#
# class Tag(StoredObject):
#
#     _id = fields.StringField(primary=True)
#     count_public = fields.IntegerField(default=0)
#     count_total = fields.IntegerField(default=0)
#
# Tag.set_storage(storage.MongoStorage(database, 'tag'))
#
# class Node(StoredObject):
#
#     _id = fields.StringField(primary=True)
#
#     date_created = fields.DateTimeField()
#     is_public = fields.BooleanField()
#
#     is_deleted = fields.BooleanField(default=False)
#     deleted_date = fields.DateTimeField()
#
#     is_registration = fields.BooleanField(default=False)
#     registered_date = fields.DateTimeField()
#
#     is_fork = fields.BooleanField(default=False)
#     forked_date = fields.DateTimeField()
#
#     title = fields.StringField()
#     description = fields.StringField()
#     category = fields.StringField()
#
#     _terms = fields.DictionaryField(list=True)
#     registered_meta = fields.DictionaryField()
#
#     files_current = fields.DictionaryField()
#     files_versions = fields.DictionaryField()
#     wiki_pages_current = fields.DictionaryField()
#     wiki_pages_versions = fields.DictionaryField()
#
#     creator = fields.ForeignField('user', backref='created')
#     contributors = fields.ForeignField('user', list=True, backref='contributed')
#     contributor_list = fields.DictionaryField(list=True)
#     users_watching_node = fields.ForeignField('user', list=True, backref='watched')
#
#     logs = fields.ForeignField('nodelog', list=True, backref='logged')
#     tags = fields.ForeignField('tag', list=True, backref='tagged')
#
#     nodes = fields.ForeignField('node', list=True, backref='parent')
#     forked_from = fields.ForeignField('node', backref='forked')
#     registered_from = fields.ForeignField('node', backref='registrations')
#
# Node.set_storage(storage.MongoStorage(database, 'node'))

# Migration

def migrate(YORM, ODM):

    yorms = YORM.find()

    for yorm in yorms:

        odm = ODM.load(yorm[ODM._primary_name])
        if odm is None:
            odm = ODM()

        for key, val in yorm.items():
            if key == '_doc' or key.startswith('_b_'):
                continue
            if key not in odm._fields:
                continue
            setattr(odm, key, val)

        # Skip records with missing PK
        if isinstance(odm._primary_key, odm._primary_type):
            odm.save()

migrate_time = {}

t0_all = time.time()

for schema in migrate_order:

    _schema_yorm = getattr(schema_yorm, schema)
    _schema_odm = globals()[schema]

    t0_schema = time.time()
    migrate(_schema_yorm, _schema_odm)
    migrate_time[schema] = time.time() - t0_schema

migrate_time['ALL'] = time.time() - t0_all

# todo: parallel examples for yORM, ODM

brian = User.find_one(Q('fullname', 'contains', 'Nosek'))

brian_nodes_created = [Node.load(nid) for nid in brian.created['node']['creator']]
brian_nodes_contributed = [Node.load(nid) for nid in brian.contributed['node']['contributors']]

logging.debug(
    'Brian has created {} projects.'.format(
        len(brian.created['node']['creator'])
    )
)
logging.debug(
    'Brian has contributed to {} projects.'.format(
        len(brian.contributed['node']['contributors'])
    )
)

logging.debug(pprint.pprint(migrate_time))

for collection_name in ['pagecounters', 'useractivitycounters']:

    old_records = schema_yorm.db[collection_name].find()
    database[collection_name].remove()
    database[collection_name].insert(old_records)