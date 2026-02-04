"""Consolidates all signals used by the OSF."""

from framework.auth import signals as auth
from website.project import signals as project
from addons.base import signals as event
from website.reviews import signals as reviews


ALL_SIGNALS = [  # TODO: Fix
    project.unreg_contributor_added,
    project.contributor_added,
    project.contributor_removed,
    project.node_deleted,
    auth.user_confirmed,
    auth.user_email_removed,
    auth.user_registered,
    auth.user_account_deactivated,
    auth.user_account_reactivated,
    auth.user_account_merged,
    auth.unconfirmed_user_created,
    event.file_updated,
    reviews.reviews_email
]
