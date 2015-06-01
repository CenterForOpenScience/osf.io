"""Consolidates all signals used by the OSF."""

from framework.auth import signals as auth
from website.project import signals as project


ALL_SIGNALS = [
    auth.contributor_removed,
    auth.node_deleted,
    project.unreg_contributor_added,
    auth.user_confirmed,
    auth.user_email_removed,
    auth.user_registered,
]
