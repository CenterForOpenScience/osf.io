from website.app import setup_django
setup_django()

import sys
import time
import logging

from django.core.paginator import Paginator

from osf.models import PreprintService
from osf_tests.factories import ProjectFactory, PreprintFactory, AuthUserFactory, PreprintProviderFactory

from website.identifiers.clients import CrossRefClient

from website.app import init_app
from website import settings


logger = logging.getLogger(__name__)

PAGE_SIZE = 5


def register_existing_preprints_with_crossref(dry=True):
    """This should do three things:
    one, create a CSV of all preprints to be migrated for use by CNRI,
    two, send metadata about the new preprint DOIs to CrossRef for registration,
    three, add the new crossref specific DOIs to the preprint with the category 'doi' while marking the
    legacy_doi identifier as deleted.
    """
    paginator = Paginator(
        PreprintService.objects.filter(identifiers__category='legacy_doi', identifiers__deleted__isnull=True).order_by('pk'),
        PAGE_SIZE
    )
    client = CrossRefClient(base_url=settings.CROSSREF_URL)

    # Write the header for the "good" dois to convert
    with open('preprint_doi_conversions.csv', 'w') as doi_file:
        doi_file.write('legacy_doi, new_doi\n')

    # Keep track of any faulty DOIs that won't be converted for now
    with open('preprints_with_faulty_dois.csv','w') as bad_dois:
        bad_dois.write('guid, legacy_doi, new_doi\n')

    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        preprints_to_migrate = []
        batch_metadata = []
        for preprint in page:
            legacy_doi_identifier = preprint.get_identifier(category = 'legacy_doi')
            new_doi = client.build_doi(preprint)

            # Some DOIs it seems have None as their handle -- keep track of those and don't port them for now
            if 'None' in legacy_doi_identifier.value:
                with open('preprints_with_faulty_dois.csv','a') as bad_dois:
                    bad_dois.write('{}, {}, {}\n'.format(preprint._id, legacy_doi_identifier.value, new_doi))
                continue

            # write a row to the CSV file
            with open('preprint_doi_conversions.csv', 'a') as doi_file:
                doi_file.write('{}, {}\n'.format(legacy_doi_identifier.value, new_doi))

            # set new DOI and mark old legacy doi as deleted
            if not dry:
                preprint.set_identifier_value(category='doi', value=new_doi)
                legacy_doi_identifier.remove()

        # build batch metadata to send to CrossRef
        bulk_preprint_metadata = client.build_metadata(page.object_list)

        if dry:
            logger.info('Here is the bulk metadata I would have sent:\n {}'.format(bulk_preprint_metadata))
        else:
            client.create_identifier(metadata=bulk_preprint_metadata, doi='test_{}.xml'.format(page_num))
            logger.info('Just sent off XML to crossref for {} preprints'.format(len(page.object_list)))

        if page.has_next():
            logger.info('Waiting 5 seconds...')
            time.sleep(5)
        else:
            logger.info('All done!')


def main(dry):
    register_existing_preprints_with_crossref(dry)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    main(dry=dry)
