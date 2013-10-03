from framework import db, storage
from framework.auth.model import User
from framework.search.model import Keyword
from website.project.model import (ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
                                   Tag, WatchConfig)
from framework.mongo import set_up_storage


models = [User, ApiKey, Keyword, ApiKey, Node, NodeLog, NodeFile, NodeWikiPage, Tag, WatchConfig]

set_up_storage(models, storage.MongoStorage, db=db)
