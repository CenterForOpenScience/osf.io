import time

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import connection

from osf.models import NotificationSubscription, NotificationSubscriptionLegacy


class Command(BaseCommand):
    """
        Usage example:
        python manage.py migrate_notifications_verification
        python manage.py migrate_notifications_verification --duplicates --distribution
        python manage.py migrate_notifications_verification --duplicates --unique-digest --output-size=100
    """

    help = 'Verify notification migration integrity (duplicates, invalid frequencies, counts and distribution)'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', default=False, help='Run all checks')
        parser.add_argument('--duplicates', action='store_true', help='Check for duplicate NotificationSubscription entries')
        parser.add_argument('--frequencies', action='store_true', help='Check message_frequency values for invalid ones')
        parser.add_argument('--counts', action='store_true', help='Compare legacy M2M total with migrated count')
        parser.add_argument('--distribution', action='store_true', help='Print breakdown summary')
        parser.add_argument('--unique-digest', action='store_true', default=False, help='Used along with --duplicates to include _is_digest field in unique_together')
        parser.add_argument('--output-size', type=int, default=10, help='Used along with other options to set the number of found duplicates for output')

    def handle(self, *args, **options):

        start = time.time()
        flags = {k for k, v in options.items() if v and k in ['duplicates', 'frequencies', 'counts', 'distribution']}
        run_all = options['all']
        output_size = options['output_size']

        print('\n================ Notification Migration Verification ================\n')

        if not run_all and not flags:
            print('\n⚠ No options selected, command will exit ... \n')

        # 1. Detect duplicates
        if run_all or 'duplicates' in flags:
            print(f'1) Checking duplicate NotificationSubscription entries (unique-digest:{options['unique_digest']})...')
            if options['unique_digest']:
                duplicates = (
                    NotificationSubscription.objects.values(
                        'user_id', 'content_type_id', 'object_id', 'notification_type_id', '_is_digest',
                    )
                    .annotate(count=Count('id'))
                    .filter(count__gt=1)
                )
            else:
                duplicates = (
                    NotificationSubscription.objects.values(
                        'user_id', 'content_type_id', 'object_id', 'notification_type_id',
                    )
                    .annotate(count=Count('id'))
                    .filter(count__gt=1)
                )
            print(f'   → Duplicates found: {duplicates.count()}.')
            if duplicates.exists():
                print(f'   Sample (up to {output_size}):')
                for d in duplicates.order_by('-count')[:output_size]:
                    print('    ', d)
            print('   ✔ OK' if not duplicates.exists() else '   ⚠ Needs review')

        # 2. Invalid frequencies
        if run_all or 'frequencies' in flags:
            print('\n2) Checking invalid message_frequency values...')
            valid = {'none', 'daily', 'instantly'}
            invalid_freq = NotificationSubscription.objects.exclude(message_frequency__in=valid)

            print(f'   → Invalid frequency rows: {invalid_freq.count()}')
            if invalid_freq.exists():
                print('   Sample (id, freq):')
                for row in invalid_freq[:output_size]:
                    print(f'     {row.id} → {row.message_frequency}')
            print('   ✔ OK' if not invalid_freq.exists() else '   ⚠ Needs cleanup')

        # 3. Compare legacy frequency-based totals vs new subscription count
        if run_all or 'counts' in flags:
            print('\n3) Validating total count migrated...')
            valid_subscription_ids = NotificationSubscriptionLegacy.objects.filter(event_name__in=['global_reviews', 'global_file_updated', 'file_updated']).values_list('id', flat=True)
            with connection.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM osf_notificationsubscriptionlegacy_none where notificationsubscription_id IN %s', [tuple(valid_subscription_ids)])
                none_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM osf_notificationsubscriptionlegacy_email_digest where notificationsubscription_id IN %s', [tuple(valid_subscription_ids)])
                digest_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM osf_notificationsubscriptionlegacy_email_transactional where notificationsubscription_id IN %s', [tuple(valid_subscription_ids)])
                transactional_count = cursor.fetchone()[0]

            legacy_total_expanded = none_count + digest_count + transactional_count
            new_total = NotificationSubscription.objects.count()

            print(f'   Legacy M2M total:      {legacy_total_expanded}')
            print(f'   New subscriptions:     {new_total}')

            if legacy_total_expanded == new_total:
                print('   ✔ Counts match')
            else:
                diff = new_total - legacy_total_expanded
                print(f'   ⚠ Mismatch: difference = {diff} (possibly skipped, duplicates removed or newly created)')

                print('   ⚠ Note: this is accurate only right after migration and before any new subscriptions are created.)')

        if run_all or 'distribution' in flags:
            # 4. Distribution summary
            print(f'\n4) Subscription distribution breakdown (top {output_size}):\n')
            dist = (
                NotificationSubscription.objects
                .values('notification_type_id', 'message_frequency')
                .annotate(total=Count('id'))
                .order_by('-total')[:output_size]
            )
            for row in dist:
                print('  ', row)

        elapsed = time.time() - start
        print(f'\n================ Verification complete in {elapsed:.2f}s ================\n')
