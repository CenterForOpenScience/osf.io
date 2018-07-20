"""Mark specified nodes as spam.

    python manage.py confirm_spam abc12
"""
import logging

from django.core.management.base import BaseCommand
from osf.models import Guid, PreprintService

logger = logging.getLogger(__name__)

def confirm_spam(guid):
    is_preprint = isinstance(guid.referent, PreprintService)
    node, referent_type = (guid.referent.node, 'preprint') if is_preprint else (guid.referent, 'node')

    logger.info('Marking {} {} as spam...'.format(referent_type, guid.referent._id))
    content = node._get_spam_content(saved_fields={'is_public', } | node.SPAM_CHECK_FIELDS)[:300]
    # spam_data must be populated in order for confirm_spam to work
    guid.referent.spam_data['headers'] = {
        'Remote-Addr': '',
        'User-Agent': '',
        'Referer': '',
    }
    guid.referent.spam_data['content'] = content
    guid.referent.spam_data['author'] = node.creator.fullname
    guid.referent.spam_data['author_email'] = node.creator.username
    guid.referent.confirm_spam()
    guid.referent.save()
    if not is_preprint:
        for preprint in guid.referent.preprints.get_queryset():
            logger.info('Marked preprint {} of node {} as spam...'.format(preprint._id, guid.referent._id))
            preprint.confirm_spam(save=True)

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('guids', type=str, nargs='+', help='List of Node or Preprint GUIDs')

    def handle(self, *args, **options):
        guids = options.get('guids', [])
        for guid in Guid.objects.filter(_id__in=guids):
            confirm_spam(guid)
