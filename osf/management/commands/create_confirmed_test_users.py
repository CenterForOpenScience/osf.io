import logging
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from osf.models import OSFUser, UserActivityCounter
from website.app import setup_django
from website.security import random_string

setup_django()


logger = logging.getLogger(__name__)


def generate_users(prefix, suffix, domain, total):
    """Generate usernames paired with full names.
    """
    return {
        f'{prefix}+{str(i).zfill(4)}+{suffix}@{domain}': f'{prefix}{str(i).zfill(4)} {suffix}{str(i).zfill(4)}'
        for i in range(1, total + 1)
    }


def create_confirmed_test_users(
        prefix,
        suffix='enter',
        domain='cos.io',
        total=100,
        password=None,
        set_activity=True,
        dry_run=False
):
    """Create a given number of confirmed users, with generated usernames and full names. For each created user,
    optionally creates a matching UserActivityCounter entry with a random total between 1 and 100.
    """
    created_user_ids = []
    username_to_fullname = generate_users(prefix, suffix, domain, total)

    for raw_username, fullname in username_to_fullname.items():
        username = raw_username.lower().strip()
        user_password = password or random_string(16)
        if dry_run:
            logger.info(f'Dry run: would create confirmed user "{username}" ({fullname}).')
            continue
        try:
            user = OSFUser.create_confirmed(
                username=username,
                password=user_password,
                fullname=fullname,
            )
        except Exception as e:
            logger.error(f'Failed to create confirmed user "{username}" ({fullname}): error={e}.')
            continue
        user.accepted_terms_of_service = timezone.now()
        user.save()
        logger.info(f'Created confirmed user "{username}" ({fullname})')
        created_user_ids.append(user._id)

    if set_activity:
        UserActivityCounter.objects.bulk_create(
            [
                UserActivityCounter(
                    _id=_id,
                    action={},
                    date={},
                    total=random.randint(1, 100)
                )
                for _id in created_user_ids
            ],
            ignore_conflicts=True,
        )

    logger.info(f'Done. Created {len(created_user_ids)} user(s); skipped {len(username_to_fullname) - len(created_user_ids)}.')


class Command(BaseCommand):
    help = '''Create a given number of confirmed users, with generated usernames and full names.

    python3 manage.py create_confirmed_test_users --prefix longze --suffix enter --domain cos.io --total 100
    '''

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--prefix',
            type=str,
            required=True,
            help='Prefix for generated usernames and full names',
        )
        parser.add_argument(
            '--suffix',
            type=str,
            default='enter',
            help='Suffix for generated usernames and full names',
        )
        parser.add_argument(
            '--domain',
            type=str,
            default='cos.io',
            help='Domain for generated usernames',
        )
        parser.add_argument(
            '--total',
            type=int,
            default=100,
            help='Total number of users to create',
        )
        parser.add_argument(
            '--password',
            type=str,
            dest='password',
            help='Password to set for every created user.',
        )
        parser.add_argument(
            '--no-activity',
            action='store_true',
            dest='no_activity',
            help='Skip setting a random activity total for the created users',
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run; log what would happen without creating any users',
        )

    def handle(self, *args, **options):
        prefix = options.get('prefix')
        suffix = options.get('suffix')
        domain = options.get('domain')
        total = options.get('total')
        password = options.get('password')
        set_activity = not options.get('no_activity', False)
        dry_run = options.get('dry_run', False)

        if dry_run:
            logger.info('This is a dry run; no users will be created.')

        with transaction.atomic():
            create_confirmed_test_users(
                prefix,
                suffix=suffix,
                domain=domain,
                total=total,
                password=password,
                set_activity=set_activity,
                dry_run=dry_run,
            )
