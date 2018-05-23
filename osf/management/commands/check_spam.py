"""Check nodes for spam using Akismet.

To print out whether a node is classified as spam or ham:

    python manage.py check_spam abc12


To check and flag a node:

    python manage.py check_spam abc12 --flag
"""
import logging

from django.core.management.base import BaseCommand
from osf.models import Guid, PreprintService

logger = logging.getLogger(__name__)

def check_spam(guid, flag=False):
    """Check and optionally flag a node as spam. Unlike the spam-related node methods, this
    function will check the node regardless of whether the node is public or private.
    """
    is_preprint = isinstance(guid.referent, PreprintService)
    node, referent_type = (guid.referent.node, 'preprint') if is_preprint else (guid.referent, 'node')
    logger.info('Checking {} {}...'.format(referent_type, guid.referent._id))

    # Pass saved fields so that all relevant fields get sent to Akismet
    content = node._get_spam_content(saved_fields={'is_public', } | node.SPAM_CHECK_FIELDS)

    author = node.creator.fullname
    author_email = node.creator.username
    # Required by Node#do_check_spam
    request_headers = {
        'Remote-Addr': ''
    }
    is_spam = node.do_check_spam(
        author=author,
        author_email=author_email,
        content=content,
        request_headers=request_headers,
        update=flag
    )
    logger.info('{} {} spam? {}'.format(referent_type, guid.referent._id, is_spam))
    if is_spam and flag:
        logger.info('Flagged {} {} as spam...'.format(referent_type, guid.referent._id))
        node.save()
        if not is_preprint:
            for preprint in node.preprints.get_queryset():
                logger.info('Flagged preprint {} of node {} as spam...'.format(preprint._id, guid.referent._id))
                preprint.flag_spam()
                preprint.save()

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--flag',
            action='store_true',
            dest='flag',
            help='Update records in the database',
        )
        parser.add_argument('guids', type=str, nargs='+', help='List of Node or Preprint GUIDs')

    def handle(self, *args, **options):
        guids = options.get('guids', [])
        flag = options.get('flag', False)

        for guid in Guid.objects.filter(_id__in=guids):
            check_spam(guid, flag=flag)
