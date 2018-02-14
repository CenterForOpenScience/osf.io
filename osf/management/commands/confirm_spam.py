"""Mark specified nodes as spam.

    python manage.py confirm_spam abc12
"""
import logging

from django.core.management.base import BaseCommand
from osf.models import AbstractNode

logger = logging.getLogger(__name__)

def confirm_spam(node):
    content = node._get_spam_content(saved_fields={'is_public', } | node.SPAM_CHECK_FIELDS)[:300]
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
        parser.add_argument('guids', type=str, nargs='+', help='Node GUIDs')

    def handle(self, *args, **options):
        guids = options.get('guids', [])
        for node in AbstractNode.objects.filter(guids___id__in=guids):
            logger.info('Marking AbstractNode {} as spam...'.format(node._id))
            confirm_spam(node)
