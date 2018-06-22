# -*- coding: utf-8 -*-
"""Send a CSV to support@osf.io containing legacy preprint DOIs and new DOIs created with Crossref.
This should only be run after all preprints have new Crossref DOIS (using scripts/remove_after_use/register_existing_preprints_with_crossref.py)
"""
import io
import csv
import sys
import gzip
import logging

from website.app import setup_django
setup_django()
from django.contrib.contenttypes.models import ContentType
from django.db.models import Subquery, OuterRef
import progressbar

from osf.models import PreprintService, Identifier

from website import mails
from website import settings
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def send_doi_csv(dry=True):
    preprint_ct = ContentType.objects.get_for_model(PreprintService)

    new_doi_subquery = (
        Identifier.objects.filter(category='doi',
                                  content_type=preprint_ct,
                                  object_id=OuterRef('object_id')).values('value')
    )
    qs = (
        Identifier.objects.filter(category='legacy_doi',
                                  content_type=preprint_ct)
                          .annotate(new_doi=Subquery(new_doi_subquery))
    )
    progress_bar = progressbar.ProgressBar(maxval=qs.count()).start()

    # CSV for dois to convert
    conversion_output = io.BytesIO()
    conversion_writer = csv.DictWriter(conversion_output, fieldnames=['legacy_doi', 'new_doi'])
    conversion_writer.writeheader()

    # Some DOIs it seems have None as their handle -- keep track of those and don't convert them for now
    bad_doi_output = io.BytesIO()
    bad_doi_writer = csv.DictWriter(bad_doi_output, fieldnames=['preprint_pk', 'legacy_doi', 'new_doi'])
    bad_doi_writer.writeheader()
    there_are_doi_errors = False

    for i, identifier in enumerate(qs):
        progress_bar.update(i + 1)
        legacy_doi = identifier.value
        new_doi = identifier.new_doi
        if 'None' in legacy_doi or not new_doi:
            there_are_doi_errors = True
            bad_doi_writer.writerow({
                'preprint_pk': identifier.object_id,
                'legacy_doi': legacy_doi,
                'new_doi': new_doi,
            })
            continue
        else:
            conversion_writer.writerow({
                'legacy_doi': legacy_doi,
                'new_doi': new_doi,
            })
    progress_bar.finish()

    conversion_filename = 'legacy_to_crossref_preprint_dois.csv'
    if dry:
        logger.info('[dry] Skipping email of {}'.format(conversion_filename))
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
            logger.error('[dry] Skipping email of {}'.format(error_filename))
            logger.error(bad_doi_output.getvalue())
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
    send_doi_csv(dry)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
