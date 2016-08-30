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
    AlternativeCitation,
    DraftRegistration,
    DraftRegistrationLog, PreprintProvider
)
from website.project.sanctions import (
    DraftRegistrationApproval,
    Embargo,
    EmbargoTerminationApproval,
    RegistrationApproval,
    Retraction,
)
from website.oauth.models import ApiOAuth2Application, ExternalAccount, ApiOAuth2PersonalToken
from website.identifiers.model import Identifier
from website.citations.models import CitationStyle
from website.institutions.model import Institution  # flake8: noqa

from website.mails import QueuedMail
from website.files.models.base import FileVersion
from website.files.models.base import StoredFileNode
from website.files.models.base import TrashedFileNode
from website.conferences.model import Conference, MailRecord
from website.mailing_list.model import MailingListEventLog
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.archiver.model import ArchiveJob, ArchiveTarget
from website.project.licenses import NodeLicense, NodeLicenseRecord
from website.project.taxonomies import Subject

# All models
MODELS = (
    AlternativeCitation,
    ApiOAuth2Application,
    ApiOAuth2PersonalToken,
    ArchiveJob,
    ArchiveTarget,
    BlacklistGuid,
    CitationStyle,
    CitationStyle,
    Comment,
    Conference,
    DraftRegistration,
    DraftRegistrationApproval,
    DraftRegistrationLog,
    Embargo,
    EmbargoTerminationApproval,
    ExternalAccount,
    FileVersion,
    Guid,
    Identifier,
    MailRecord,
    MetaData,
    MetaSchema,
    Node,
    NodeLicense,
    NodeLicenseRecord,
    NodeLog,
    NotificationDigest,
    NotificationSubscription,
    Pointer,
    PreprintProvider
    PrivateLink,
    QueuedMail,
    RegistrationApproval,
    Retraction,
    Session,
    StoredFileNode,
    Subject,
    Tag,
    TrashedFileNode,
    User,
    WatchConfig
    )

GUID_MODELS = (User, Node, Comment, MetaData)
