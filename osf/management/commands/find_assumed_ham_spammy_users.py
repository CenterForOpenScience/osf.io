import csv
import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from framework import sentry
from osf.models import NotableDomain, OSFUser
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


def fix_user(user):
    """Reset the user to a clean, active state. Returns False if the user needs manual review."""
    if user.spam_data.get('who_flagged'):
        # reported by other people -- leave for staff to decide
        return False
    user.spam_data.pop('domains', None)
    user.unspam()
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
            if options['fix']:
                try:
                    action = 'fixed' if fix_user(user) else 'needs_review'
                except Exception as exc:
                    sentry.log_exception(exc)
                    action = 'error'
                fixed += action == 'fixed'
            logger.info(f'{user._id} {user.username} spam_status={status} -> {action}')
            rows.append([user._id, user.username, status, user.spam_data.get('domains', ''), action])

        if options['output']:
            with open(options['output'], 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['guid', 'username', 'spam_status', 'spam_domains', 'action'])
                writer.writerows(rows)
        logger.info(f'Found {len(rows)} assumed-HAM spammy users; fixed {fixed}.')
