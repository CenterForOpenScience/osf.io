# -*- coding: utf-8 -*-
import io
import csv
import sys
import gzip
import time
import logging

from website.app import setup_django
setup_django()
from django.core.paginator import Paginator

from osf.models import PreprintService
from osf_tests.factories import ProjectFactory, PreprintFactory, AuthUserFactory, PreprintProviderFactory

from website import mails
from website import settings
from website.app import init_app
from website.identifiers.clients import CrossRefClient


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
        PreprintService.objects.filter(
            identifiers__category='legacy_doi',
            identifiers__deleted__isnull=True
        ).select_related('provider').order_by('pk'),
        PAGE_SIZE
    )
    client = CrossRefClient(base_url=settings.CROSSREF_URL)

    # CSV for dois to convert
    conversion_output = io.BytesIO()
    conversion_writer = csv.writer(conversion_output)
    conversion_writer.writerow(['legacy_doi', 'new_doi'])

    # Some DOIs it seems have None as their handle -- keep track of those and don't convert them for now
    bad_doi_output = io.BytesIO()
    bad_doi_writer = csv.writer(bad_doi_output)
    bad_doi_writer.writerow(['guid', 'legacy_doi', 'new_doi'])
    there_are_doi_errors = False

    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        preprints_to_migrate = []
        batch_metadata = []
        for preprint in page:
            legacy_doi = preprint.get_identifier(category = 'legacy_doi').value

            if 'None' in legacy_doi:
                bad_doi_writer.writerow([preprint._id, legacy_doi, new_doi])
                there_are_doi_errors = True
                continue

            new_doi = client.build_doi(preprint)
            conversion_writer.writerow([legacy_doi, new_doi])

        # build batch metadata to send to CrossRef
        bulk_preprint_metadata = client.build_metadata(page.object_list)

        if dry:
            logger.info('Here is the bulk metadata I would have sent:\n {}'.format(bulk_preprint_metadata))
        else:
            client.bulk_create(metadata=bulk_preprint_metadata, filename='osf_dois_{}.xml'.format(page_num))
            logger.info('Just sent off XML to crossref for {} preprints'.format(len(page.object_list)))

        if page.has_next():
            logger.info('Waiting 5 seconds...')
            time.sleep(5)
        else:
            logger.info('All done!')

    conversion_filename = 'legacy_to_crossref_preprint_dois.csv'
    if dry:
        print(conversion_output.getvalue())
    else:
        # Create gzip files for the conversion CSV, send an email with that as an attachment
        conversion_gzip = io.BytesIO()
        conversion_filename = conversion_filename + '.gz'
        with gzip.GzipFile(filename=conversion_filename, mode='wb', fileobj=conversion_gzip) as conversion_gzip_obj:
            conversion_gzip_obj.write(conversion_output.getvalue())

            mails.send_mail(
                mail=mails.CROSSREF_CSV,
                to_addr=settings.OSF_SUPPORT_EMAIL,
                message='This CSV contains the DOIs to be sent to CNI to update the pointers from the old EZID DOI to the fancy new CrossRef DOI.',
                attachment_name=conversion_filename,
                attachment_content=conversion_gzip.getvalue(),
                csv_type='Converting Preprint DOIs from EZID to CrossRef',
                celery=False  # for the non-JSON-serializable attachment
            )

    # Check to see if there were rows added to the error CSV, send seperate email if so
    if there_are_doi_errors:
        error_filename = 'dois_with_errors.csv'
        if dry:
            with open(error_filename, 'w') as f:
                f.write(bad_doi_output.getvalue())
        else:
            error_filename = error_filename + '.gz'
            error_gzip = io.BytesIO()
            with gzip.GzipFile(filename=error_filename, mode='wb', fileobj=error_gzip) as error_gzip_obj:
                error_gzip_obj.write(bad_doi_output.getvalue())

            mails.send_mail(
                mail=mails.CROSSREF_CSV,
                to_addr=settings.OSF_SUPPORT_EMAIL,
                message='This CSV contains the DOIs that appear to have NONE in the DOI value, and should be investigated further.',
                attachment_name=error_filename,
                attachment_content=error_gzip.getvalue(),
                csv_type='DOIs that may have errored and have not been converted',
                celery=False  # for the non-JSON-serializable attachment
            )

def main(dry):
    register_existing_preprints_with_crossref(dry)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    main(dry=dry)
