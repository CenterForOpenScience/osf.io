# -*- coding: utf-8 -*-
'''Consolidates all necessary models from the framework and website packages.
'''

from framework.guid.model import Guid
from framework.auth.model import User
from framework.sessions.model import Session

from website.project.model import (
    ApiKey, Node, NodeLog,
    Tag, WatchConfig, MetaData, MetaSchema,
    MailRecord,
)

# All models
MODELS = (
    User, ApiKey, Node, NodeLog,
    Tag, WatchConfig, Session, Guid, MetaData, MetaSchema,
    MailRecord,
)

GUID_MODELS = (User, Node, Tag, MetaData)
