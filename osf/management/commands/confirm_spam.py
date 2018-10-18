"""Mark specified nodes as spam.

    python manage.py confirm_spam abc12
"""
import logging

from django.core.management.base import BaseCommand
from osf.models import Guid, Preprint

logger = logging.getLogger(__name__)

def confirm_spam(guid):
    node = guid.referent
    referent_type = 'preprint' if isinstance(node, Preprint) else 'node'

    logger.info('Marking {} {} as spam...'.format(referent_type, node._id))

    saved_fields = {'is_public', } if referent_type == 'node' else {'is_published', }

    content = node._get_spam_content(saved_fields | node.SPAM_CHECK_FIELDS)[:300]
    # spam_data must be populated in order for confirm_spam to work
    node.spam_data['headers'] = {
        'Remote-Addr': '',
        'User-Agent': '',
        'Referer': '',
    }
    node.spam_data['content'] = content
    node.spam_data['author'] = node.creator.fullname
    node.spam_data['author_email'] = node.creator.username
    node.confirm_spam()
    node.save()


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('guids', type=str, nargs='+', help='List of Node or Preprint GUIDs')

    def handle(self, *args, **options):
        guids = options.get('guids', [])
        for guid in Guid.objects.filter(_id__in=guids):
            confirm_spam(guid)
