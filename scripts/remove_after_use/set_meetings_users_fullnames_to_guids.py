import sys
import logging

import django
from django.db import transaction
django.setup()

from osf.models import OSFUser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main():
    dry_run = '--dry' in sys.argv
    with transaction.atomic():
        users = OSFUser.objects.filter(fullname__regex=r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$', tags__name='osf4m')
        logger.info('{} users found added by OSF 4 Meetings with emails for fullnames'.format(users.count()))
        for user in users:
            user.fullname = user._id
            if not dry_run:
                user.save()

if __name__ == '__main__':
    main()
