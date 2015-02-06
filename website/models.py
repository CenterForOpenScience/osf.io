# -*- coding: utf-8 -*-
'''Consolidates all necessary models from the framework and website packages.
'''

from framework.auth.core import User
from framework.guid.model import Guid
from framework.sessions.model import Session

from website.project.model import (
    ApiKey, Node, NodeLog,
    Tag, WatchConfig, MetaSchema, Pointer,
    Comment, PrivateLink, MetaData,
)
from website.citations.models import CitationStyle
from website.conferences.model import Conference, MailRecord
from website.oauth.models import ExternalAccount

# All models
MODELS = (
    User, ApiKey, Node, NodeLog,
    Tag, WatchConfig, Session, Guid, MetaSchema, Pointer,
    MailRecord, Comment, PrivateLink, MetaData, Conference,
    CitationStyle, ExternalAccount,
)

GUID_MODELS = (User, Node, Comment, MetaData)
