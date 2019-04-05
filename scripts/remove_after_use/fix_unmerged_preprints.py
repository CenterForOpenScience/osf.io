import logging

from website.app import setup_django
setup_django()

from osf.models import OSFUser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():

    # retrieving users that are merged into oblivion
    merged_users = OSFUser.objects.filter(merged_by__isnull=False)

    for user in merged_users:
        merged_by = user.merged_by
        merged_by._merge_users_preprints(user)


if __name__ == '__main__':
    main()
