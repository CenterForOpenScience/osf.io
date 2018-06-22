# -*- coding: utf-8 -*-
import sys
import time
import logging

from website.app import setup_django
setup_django()
from django.core.paginator import Paginator
import progressbar

from osf.models import PreprintService

from website import settings
from website.identifiers.clients import CrossRefClient, ECSArXivCrossRefClient
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

PAGE_SIZE = 200


def register_existing_preprints_with_crossref(dry=True):
    """This should do three things:
    Send metadata about the new preprint DOIs to CrossRef for registration,

    The resulting mailgun callbacks
    will add the new Crossref DOIs to the preprint with the category 'doi' while marking the
    legacy_doi identifier as deleted.
    """
    # Exclude ECSArxiv because we use a different client for those
    qs = PreprintService.objects.filter(
        identifiers__category='legacy_doi',
        identifiers__deleted__isnull=True
    ).exclude(provider___id='ecsarxiv').select_related('provider', 'node', 'license__node_license').prefetch_related('node___contributors').order_by('pk')
    crossref_client = CrossRefClient(base_url=settings.CROSSREF_URL)
    logging.info('Sending {} preprints to crossref'.format(qs.count()))
    send_preprints(qs, crossref_client)

    # Send ECSArxiv preprints separately, using the ECSArXivCrossRefClient
    ecs_qs = PreprintService.objects.filter(
        identifiers__category='legacy_doi',
        identifiers__deleted__isnull=True
    ).filter(provider___id='ecsarxiv').select_related('provider', 'node', 'license__node_license').prefetch_related('node___contributors').order_by('pk')
    ecs_crossref_client = ECSArXivCrossRefClient(base_url=settings.CROSSREF_URL)
    logging.info('Sending {} ECSArXiv preprints to crossref'.format(ecs_qs.count()))
    send_preprints(ecs_qs, ecs_crossref_client)

def send_preprints(qs, client):
    paginator = Paginator(
        qs,
        PAGE_SIZE
    )
    count = qs.count()
    if count:
        progress_bar = progressbar.ProgressBar(maxval=count).start()
        n_processed = 0
        for page_num in paginator.page_range:
            page = paginator.page(page_num)
            # build batch metadata to send to CrossRef
            bulk_preprint_metadata = client.build_metadata(page.object_list)
            preprint_ids = [e._id for e in page.object_list]
            if dry:
                logger.info('[dry] Sent metadata for preprints: {}'.format(preprint_ids))
            else:
                client.bulk_create(metadata=bulk_preprint_metadata, filename='osf_dois_{}'.format(page_num))
                logger.info('Sent metadata for preprints: {}'.format(preprint_ids))

            n_processed += len(preprint_ids)
            progress_bar.update(n_processed)
            if page.has_next():
                # Throttle requeests
                if not dry:
                    logger.info('Waiting 2 seconds...')
                    time.sleep(2)
            else:
                logger.info('All done!')
    else:
        logger.info('No preprints to update.')

def main(dry):
    register_existing_preprints_with_crossref(dry)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
