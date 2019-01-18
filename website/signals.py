"""Consolidates all signals used by the GakuNin RDM."""

from framework.auth import signals as auth
from website.project import signals as project
from addons.base import signals as event
from website.conferences import signals as conference
from website.reviews import signals as reviews

ALL_SIGNALS = [
    project.comment_added,
    project.mention_added,
    project.unreg_contributor_added,
    project.contributor_added,
    project.contributor_removed,
    project.privacy_set_public,
    project.node_deleted,
    auth.user_confirmed,
    auth.user_email_removed,
    auth.user_registered,
    auth.user_merged,
    auth.unconfirmed_user_created,
    event.file_updated,
    conference.osf4m_user_created,
    reviews.reviews_email
]
