import logging

from django.core.management.base import BaseCommand

from osf.models import PreprintProvider, OSFUser

PAGE_SIZE = 100

PROVIDER_WITHDRAWAL_COMMENT = {
    'eartharxiv': 'This preprint was moved to the new EartharXiv hosted by CDL. The DOI now resolves to the new location at https://eartharxiv.org/.'
}

logger = logging.getLogger(__name__)


def withdraw_all_preprints(provider_id, page_size, user_guid, comment=None):
    """ A management command to withdraw all preprints from a specified provider
        Created to withdraw all EarthRxiv preprints, but can be used for any preprint
        provider
    """
    provider = PreprintProvider.load(provider_id)
    if not provider:
        raise RuntimeError('Could not find provider. Check ID and try again')

    user = OSFUser.load(user_guid)
    if not user:
        raise RuntimeError('Could not find user. Check GUID and try again')

    saved_comment = PROVIDER_WITHDRAWAL_COMMENT.get(provider_id, None)
    if not comment and saved_comment:
        comment = saved_comment

    if not comment and not saved_comment:
        raise RuntimeError('Comment not provided!')

    preprints = provider.preprints.filter(date_withdrawn=None, is_published=True)[:page_size]

    preprints_withdrawn = 0

    for preprint in preprints:
        preprint.run_withdraw(user, comment)
        preprint.reload()
        assert preprint.is_retracted
        preprints_withdrawn += 1

        logger.info(f'{preprints_withdrawn} have been withdrawn from provider {provider.name}')


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--provider-id',
            dest='provider_id',
            help='ID of the preprint provider to withdraw',
        )
        parser.add_argument(
            '--page-size',
            dest='page_size',
            help='How many preprints to withdraw this run.'
        )
        parser.add_argument(
            '--user',
            dest='user_guid',
            help='User to use as action creator.'
        )
        parser.add_argument(
            '--comment',
            dest='comment',
            help='Comment to withdraw with'
        )

    def handle(self, *args, **options):
        provider_id = options.get('provider_id', None)
        page_size = int(options.get('page_size', PAGE_SIZE))
        user_guid = options.get('user_guid', None)
        comment = options.get('comment', None)

        if not provider_id:
            raise RuntimeError('Must provide a provider id.')

        if not user_guid:
            raise RuntimeError('Must provider a user to use as action creator.')

        withdraw_all_preprints(provider_id, page_size, user_guid, comment)
