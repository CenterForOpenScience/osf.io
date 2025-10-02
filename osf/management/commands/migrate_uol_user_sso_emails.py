import logging
from contextlib import redirect_stdout

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import Email, Node

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-d',
            '--dry',
            action='store_true',
            dest='dry_run',
            help='If true, check institution and region only'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if dry_run:
            logger.warning('Dry Run: This is a dry-run pass!')
        with transaction.atomic():
            conflicts = migrate_uol_user_sso_email()
            verify_uol_user_sso_email_migration(conflicts)
            if dry_run:
                raise RuntimeError('Dry run -- transaction rolled back')


def migrate_uol_user_sso_email():
    email_domain_old = '@londonexternal.ac.uk'
    email_domain_new = '@london.ac.uk'
    eligible_emails = Email.objects.filter(address__endswith=email_domain_old)
    updated = []
    skipped = []
    conflicts = []
    print('>>>> Start ...')
    with open('uol-user-sso-email-migration-output.csv', 'w') as f:
        with redirect_stdout(f):
            print('status,status_extra,user_id,primary_email,other_email,full_name')
            for email in eligible_emails:
                address_old = email.address
                address_new = address_old.replace(email_domain_old, email_domain_new)
                user = email.user
                email_list = list(user.emails.values_list('address', flat=True))
                if user.username in email_list:
                    email_list.remove(user.username)
                emails = ';'.join(email_list) if email_list else ''
                if Email.objects.filter(address=address_new).exists():
                    conflict_user = Email.objects.get(address=address_new).user
                    if user != conflict_user:
                        conflicts.append(address_new)
                        print(f'CONFLICTS,Existing user [{conflict_user._id}] found with email [{address_new}],{user._id},{user.username},{emails},{user.fullname}')
                        continue
                    print(f'SKIPPED,User [{user._id}] already has email [{address_new}],{user._id},{user.username},{emails},{user.fullname}')
                    skipped.append(address_new)
                    continue
                user.emails.create(address=address_new)
                updated.append(address_new)
                print(f'Updated, Email address [{address_new}] has been added to user [{user._id}],{user._id},{user.username},{emails},{user.fullname}')
    print(f'>>>> Updated ({len(updated)}): {updated}')
    print(f'>>>> Skipped ({len(skipped)}): {skipped}')
    print(f'>>>> Conflicts ({len(conflicts)}): {conflicts}')
    print('>>>> Done.')
    return conflicts

def verify_uol_user_sso_email_migration(conflicts):
    print('>>>> Verify migration ...')
    email_domain_old = '@londonexternal.ac.uk'
    email_domain_new = '@london.ac.uk'
    eligible_emails = Email.objects.filter(address__endswith=email_domain_old)
    for email in eligible_emails:
        address_old = email.address
        address_new = address_old.replace(email_domain_old, email_domain_new)
        if address_new not in conflicts:
            assert address_new in list(email.user.emails.values_list('address', flat=True))
    print('>>>> Migration verified.')

def get_uol_node_contributors(node_id_list):
    if not node_id_list:
        print('>>>> Empty list')
        return
    for node_id in node_id_list:
        print(f'>>>> Processing node: {node_id} ...')
        with open(f'uol-node-contributors-{node_id}.csv', 'w') as f:
            with redirect_stdout(f):
                print('user_id,primary_email,other_emails,full_name')
                for user in Node.objects.get(guids___id=node_id).contributors.all():
                    email_list = list(user.emails.values_list('address', flat=True))
                    if user.username in email_list:
                        email_list.remove(user.username)
                    emails = ';'.join(email_list) if email_list else ''
                    print(f'{user._id},{user.username},{emails},{user.fullname}')
        print('>>>> ... Done')
    print('>>>> All done.')
