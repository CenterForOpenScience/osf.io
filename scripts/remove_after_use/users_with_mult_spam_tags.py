import logging

from website.app import setup_django
setup_django()

from osf.models import OSFUser

logger = logging.getLogger(__name__)

SPAM_TAGS= ['spam_flagged', 'spam_confirmed', 'ham_confirmed']


def find_users_with_multiple_spam_tags():
    users_with_tag = OSFUser.objects.filter(tags__name__in=SPAM_TAGS)
    multiple_tags = []
    for user in users_with_tag:
        if user.all_tags.filter(name__in=SPAM_TAGS, system=True).count() > 1:
            multiple_tags.append(user._id)

    return set(multiple_tags)


if __name__=='__main__':
    users_with_mult_tags = find_users_with_multiple_spam_tags()
    logger.info('There are {} users with multiple spam tags'.format(len(users_with_mult_tags)))
    logger.info(users_with_mult_tags)
