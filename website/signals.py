"""Consolidates all signals used by the OSF."""

from framework.auth.signals import user_registered, user_confirmed
from website.project.model import unreg_contributor_added


ALL_SIGNALS = [user_registered, unreg_contributor_added, user_confirmed]
