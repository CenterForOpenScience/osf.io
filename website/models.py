# -*- coding: utf-8 -*-
"""Consolidates all necessary models from the framework and website packages.
"""

from framework.auth.core import User
from framework.guid.model import Guid, BlacklistGuid
from framework.sessions.model import Session

from website.project.model import (
    Node, NodeLog,
    Tag, WatchConfig, MetaSchema, Pointer,
    Comment, PrivateLink, MetaData,
    Retraction, Embargo, RegistrationApproval,
    DraftRegistrationApproval, DraftRegistration,
)
from website.oauth.models import ApiOAuth2Application, ExternalAccount, ApiOAuth2PersonalToken
from website.identifiers.model import Identifier
from website.citations.models import CitationStyle

from website.mails import QueuedMail
from website.files.models.base import FileVersion
from website.files.models.base import StoredFileNode
from website.files.models.base import TrashedFileNode
from website.conferences.model import Conference, MailRecord
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.archiver.model import ArchiveJob, ArchiveTarget
from website.project.licenses import NodeLicense, NodeLicenseRecord

# All models
MODELS = (
    User, ApiOAuth2Application, ApiOAuth2PersonalToken, Node,
    NodeLog, StoredFileNode, TrashedFileNode, FileVersion,
    Tag, WatchConfig, Session, Guid, MetaSchema, Pointer,
    MailRecord, Comment, PrivateLink, MetaData, Conference,
    NotificationSubscription, NotificationDigest, CitationStyle,
    CitationStyle, ExternalAccount, Identifier,
    Embargo, Retraction, RegistrationApproval,
    ArchiveJob, ArchiveTarget, BlacklistGuid,
    QueuedMail,
    DraftRegistration, DraftRegistrationApproval,
    NodeLicense, NodeLicenseRecord
)

GUID_MODELS = (User, Node, Comment, MetaData)
