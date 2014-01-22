# -*- coding: utf-8 -*-
'''Consolidates all necessary models from the framework and website packages.
'''

from framework.guid.model import Guid
from framework.auth.model import User
from framework.sessions.model import Session

from website.project.model import (ApiKey, Node, NodeLog, NodeWikiPage,
                                   Tag, WatchConfig, MetaData, MetaSchema)

# All models
MODELS = (User, ApiKey, Node, NodeLog, NodeWikiPage,
          Tag, WatchConfig, Session, Guid, MetaData, MetaSchema)

GUID_MODELS = (User, Node, NodeWikiPage, Tag, MetaData)
