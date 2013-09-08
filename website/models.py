from framework import db, storage

from framework.auth.model import User
from framework.search.model import Keyword

User.set_storage(storage.MongoStorage(db, 'user'))
Keyword.set_storage(storage.MongoStorage(db, 'keyword'))

from website.project.model import Node, NodeLog, NodeFile, NodeWikiPage, Tag

Node.set_storage(storage.MongoStorage(db, 'node'))
NodeLog.set_storage(storage.MongoStorage(db, 'nodelog'))
NodeFile.set_storage(storage.MongoStorage(db, 'nodefile'))
NodeWikiPage.set_storage(storage.MongoStorage(db, 'nodewikipage'))
Tag.set_storage(storage.MongoStorage(db, 'tag'))
