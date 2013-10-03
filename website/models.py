from framework import db, storage

from framework.auth.model import User
from framework.search.model import Keyword
from framework.sessions.model import Session

User.set_storage(storage.MongoStorage(db, 'user'))
Keyword.set_storage(storage.MongoStorage(db, 'keyword'))
Session.set_storage(storage.MongoStorage(db, 'sessions'))

from website.project.model import ApiKey, Node, NodeLog, NodeFile, NodeWikiPage, Tag

ApiKey.set_storage(storage.MongoStorage(db, 'apikey'))
Node.set_storage(storage.MongoStorage(db, 'node'))
NodeLog.set_storage(storage.MongoStorage(db, 'nodelog'))
NodeFile.set_storage(storage.MongoStorage(db, 'nodefile'))
NodeWikiPage.set_storage(storage.MongoStorage(db, 'nodewikipage'))
Tag.set_storage(storage.MongoStorage(db, 'tag'))
