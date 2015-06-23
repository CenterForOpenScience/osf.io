# -*- coding: utf-8 -*-
"""Consolidates all necessary models from the framework and website packages.
"""

from framework.auth.core import User
from framework.guid.model import Guid, BlacklistGuid
from framework.sessions.model import Session

from website.project.model import (
    ApiKey, Node, NodeLog,
    Tag, WatchConfig, MetaSchema, Pointer,
    Comment, PrivateLink, MetaData, Retraction,
    Embargo,
)
from website.oauth.models import ExternalAccount
from website.identifiers.model import Identifier
from website.citations.models import CitationStyle
from website.conferences.model import Conference, MailRecord
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.archiver.model import ArchiveJob, ArchiveTarget

# All models
MODELS = (
    User, ApiKey, Node, NodeLog,
    Tag, WatchConfig, Session, Guid, MetaSchema, Pointer,
    MailRecord, Comment, PrivateLink, MetaData, Conference,
    NotificationSubscription, NotificationDigest, CitationStyle,
    CitationStyle, ExternalAccount, Identifier, Retraction,
    Embargo, ArchiveJob, ArchiveTarget, BlacklistGuid
)

GUID_MODELS = (User, Node, Comment, MetaData)
