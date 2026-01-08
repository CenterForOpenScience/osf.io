import time
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import connection
from osf.models import NotificationSubscription, NotificationSubscriptionLegacy


class Command(BaseCommand):
    help = 'Verify notification migration integrity (duplicates, invalid frequencies, counts, distribution)'
    '''
        Usage example:
        python manage.py migrate_notifications_verification
        python manage.py migrate_notifications_verification --duplicates --counts
    '''

    def add_arguments(self, parser):
        parser.add_argument('--duplicates', action='store_true', help='Check for duplicate NotificationSubscription entries')
        parser.add_argument('--frequencies', action='store_true', help='Check message_frequency values for invalid ones')
        parser.add_argument('--counts', action='store_true', help='Compare legacy M2M total with migrated count')
        parser.add_argument('--distribution', action='store_true', help='Print breakdown summary')
        parser.add_argument('--all', action='store_true', help='Run all checks')

    def handle(self, *args, **options):
        start = time.time()
        flags = {k for k, v in options.items() if v and k in ['duplicates', 'frequencies', 'counts', 'distribution']}

        run_all = options['all'] or not flags
        print('\n================ Notification Migration Verification ================\n')

        if run_all or 'duplicates' in flags:
            # 1. Detect duplicates
            print('1) Checking duplicate NotificationSubscription entries...')
            duplicates = (
                NotificationSubscription.objects.values(
                    'user_id', 'content_type_id', 'object_id', 'notification_type_id'
                )
                .annotate(count=Count('id'))
                .filter(count__gt=1)
            )
            print(f"   → Duplicates found: {duplicates.count()}")
            if duplicates.exists():
                print('   Sample (up to 10):')
                for d in duplicates[:10]:
                    print('    ', d)
            print('   ✔ OK' if not duplicates.exists() else '   ⚠ Needs review')

        if run_all or 'frequencies' in flags:
            # 2. Invalid frequencies
            print('\n2) Checking invalid message_frequency values...')
            valid = {'none', 'daily', 'instantly'}
            invalid_freq = NotificationSubscription.objects.exclude(message_frequency__in=valid)

            print(f"   → Invalid frequency rows: {invalid_freq.count()}")
            if invalid_freq.exists():
                print('   Sample (id, freq):')
                for row in invalid_freq[:10]:
                    print(f"     {row.id} → {row.message_frequency}")
            print('   ✔ OK' if not invalid_freq.exists() else '   ⚠ Needs cleanup')

        if run_all or 'counts' in flags:
            # 3. Compare legacy frequency-based totals vs new subscription count
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

            print(f"   Legacy M2M total:      {legacy_total_expanded}")
            print(f"   New subscriptions:     {new_total}")

            if legacy_total_expanded == new_total:
                print('   ✔ Counts match')
            else:
                diff = new_total - legacy_total_expanded
                print(f"   ⚠ Mismatch: difference = {diff} (possibly skipped or duplicates removed)")

        if run_all or 'distribution' in flags:
            # 4. Distribution summary
            print('\n4) Subscription distribution breakdown (top 30):\n')
            dist = (
                NotificationSubscription.objects
                .values('notification_type_id', 'message_frequency')
                .annotate(total=Count('id'))
                .order_by('-total')[:30]
            )
            for row in dist:
                print('  ', row)

        elapsed = time.time() - start
        print(f"\n================ Verification complete in {elapsed:.2f}s ================\n")
