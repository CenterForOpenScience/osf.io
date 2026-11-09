import csv
import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from framework import sentry
from osf.models import AdminLogEntry, NotableDomain, OSFUser
from osf.models.admin_log_entry import CONFIRM_SPAM
from osf.models.spam import SpamStatus

logger = logging.getLogger(__name__)


def find_assumed_ham_spammy_users():
    """Yield users that are assumed HAM (safe-listed email domain) but are FLAGGED or SPAM."""
    trusted_domains = list(
        NotableDomain.objects.filter(note=NotableDomain.Note.ASSUME_HAM_UNTIL_REPORTED).values_list('domain', flat=True)
    )
    if not trusted_domains:
        return
    domain_query = Q()
    for domain in trusted_domains:
        domain_query |= Q(emails__address__iendswith=f'@{domain}')
    candidates = (
        OSFUser.objects
        .filter(spam_status__in=[SpamStatus.FLAGGED, SpamStatus.SPAM])
        .filter(domain_query)
        .distinct()
    )
    for user in candidates.iterator(chunk_size=500):
        if user.is_assumed_ham:
            yield user


def was_marked_spam_by_staff(user):
    """True if staff manually confirmed this user as spam in the admin app.

    The single-user admin view logs ``user._id`` while the bulk view logs ``user.id``, so check both.
    """
    return AdminLogEntry.objects.filter(
        action_flag=CONFIRM_SPAM,
        object_id__in=[user._id, str(user.id)],
    ).exists()


def get_spammed_resources(user):
    """GUIDs of the user's nodes / preprints that are currently marked SPAM (e.g. cascaded from the ban)."""
    nodes = list(user.nodes.filter(spam_status=SpamStatus.SPAM).values_list('guids___id', flat=True))
    preprints = list(user.preprints.filter(spam_status=SpamStatus.SPAM).values_list('guids___id', flat=True))
    return nodes, preprints


def fix_user(user):
    """Reset the user to a clean, active state. Returns False if the user needs manual review."""
    if user.spam_data.get('who_flagged') or user.reports:
        # flagged by a spam service (akismet/oopspam) or reported by other users -- leave for staff to decide
        return False
    if was_marked_spam_by_staff(user):
        return False
    # only undo a deactivation that was caused by the ban itself, not one the user asked for
    disabled_by_ban = user.spam_status == SpamStatus.SPAM and user.is_disabled and not user.requested_deactivation
    user.spam_data.pop('domains', None)
    user.unspam()
    if disabled_by_ban:
        user.reactivate_account()
    user.save()
    return True


class Command(BaseCommand):
    help = 'Find users with an assumed-HAM (safe-listed) email domain whose spam status is FLAGGED or SPAM.'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Reset found users to UNKNOWN spam status and reactivate them.')
        parser.add_argument('--output', type=str, help='Optional path of a CSV file to write the report to.')

    def handle(self, *args, **options):
        rows = []
        fixed = 0
        for user in find_assumed_ham_spammy_users():
            status = 'SPAM' if user.spam_status == SpamStatus.SPAM else 'FLAGGED'
            action = 'reported'
            spammed_nodes, spammed_preprints = get_spammed_resources(user)
            if options['fix']:
                try:
                    action = 'fixed' if fix_user(user) else 'needs_review'
                except Exception as exc:
                    sentry.log_exception(exc)
                    action = 'error'
                fixed += action == 'fixed'
            logger.info(f'{user._id} {user.username} spam_status={status} -> {action}')
            rows.append([
                user._id, user.username, status, user.spam_data.get('domains', ''), action,
                ' '.join(spammed_nodes), ' '.join(spammed_preprints),
            ])

        if options['output']:
            with open(options['output'], 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['guid', 'username', 'spam_status', 'spam_domains', 'action', 'spammed_nodes', 'spammed_preprints'])
                writer.writerows(rows)
        logger.info(f'Found {len(rows)} assumed-HAM spammy users; fixed {fixed}.')
