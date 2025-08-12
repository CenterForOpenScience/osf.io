import os
import sys
import yaml
import subprocess
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Run all tests referenced in notifications.yaml.'

    def handle(self, *args, **options):
        notifications_path = os.path.join(os.getcwd(), 'notifications.yaml')
        
        if not os.path.exists(notifications_path):
            self.stdout.write(self.style.ERROR(f'File not found: {notifications_path}'))
            return

        with open(notifications_path, 'r') as f:
            data = yaml.safe_load(f) or {}

        test_files = set()
        for nt in data.get('notification_types', []):
            for test in nt.get('tests', []):
                if test and test.strip():
                    test_files.add(test.strip())

        if not test_files:
            self.stdout.write(self.style.WARNING('No test files found in notifications.yaml.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Running tests in {len(test_files)} files...'))
        for test_file in sorted(test_files):
            self.stdout.write(f'  - {test_file}')

        # Run pytest once for all test files
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', *sorted(test_files)]
        )

        if result.returncode != 0:
            self.stdout.write(self.style.ERROR('Some tests failed.'))
            sys.exit(result.returncode)
        else:
            self.stdout.write(self.style.SUCCESS('All tests passed.'))
