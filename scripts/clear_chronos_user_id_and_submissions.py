"""
Clears the `chronos_user_id` field on all OSFUser instances. Needed for switching from one Chronos server to another.
"""
import sys
import logging
import django
django.setup()

from osf import models

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    models.OSFUser.objects.all().update(chronos_user_id=None)
    models.ChronosSubmission.objects.all().delete()


if __name__ == '__main__':
    main(dry_run='--dry' in sys.argv)
