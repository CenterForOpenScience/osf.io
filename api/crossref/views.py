import logging

import lxml.etree
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from api.crossref.permissions import RequestComesFromMailgun
from osf.models import Preprint, NotificationTypeEnum
from osf.models.base import Guid
from website import settings
from website.preprints.tasks import mint_doi_on_crossref_fail

logger = logging.getLogger(__name__)


class ParseCrossRefConfirmation(APIView):
    # This view goes under the _/ namespace
    view_name = 'parse_crossref_confirmation_email'
    view_category = 'identifiers'

    permission_classes = (
        RequestComesFromMailgun,
    )

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_class(self):
        return None

    def post(self, request):
        crossref_email_content = lxml.etree.fromstring(request.POST['body-plain'].encode())
        status = crossref_email_content.get('status').lower()  # from element doi_batch_diagnostic
        record_count = int(crossref_email_content.find('batch_data/record_count').text)
        records = crossref_email_content.xpath('//record_diagnostic')
        dois_processed = 0

        if status == 'completed':
            guids = []
            # Keep track of errors received, ignore those that are handled
            unexpected_errors = False
            for record in records:
                doi = getattr(record.find('doi'), 'text', None)
                guid = doi.split('/')[-1] if doi else None
                guids.append(guid)
                preprint = Preprint.load(guid) if guid else None
                if record.get('status').lower() == 'success' and doi:
                    msg = record.find('msg').text
                    created = bool(msg == 'Successfully added')
                    # Unversioned DOIs (no _vN suffix, e.g. 10.31233/osf.io/tnaqp) are routing
                    # aliases that always resolve to the latest version via OSF's GUID routing.
                    # Store them as 'doi_unversioned' on the v1 preprint so we can track which
                    # preprint series have had their unversioned DOI registered.
                    _, version = Guid.split_guid(guid) if guid else (None, None)
                    if not version:
                        logger.info(f'Unversioned DOI confirmed by CrossRef: {doi}')
                        if created and guid:
                            v1_preprint = Preprint.objects.filter(
                                versioned_guids__guid___id=guid,
                                versioned_guids__version=1,
                            ).first()
                            if v1_preprint:
                                v1_preprint.set_identifier_value(category='doi_unversioned', value=doi)
                        dois_processed += 1
                        continue

                    legacy_doi = preprint.get_identifier(category='legacy_doi')
                    if created or legacy_doi:
                        # Sets preprint_doi_created and saves the preprint
                        preprint.set_identifier_values(doi=doi, save=True)
                    # Double records returned when possible matching DOI is found in crossref
                    elif 'possible preprint/vor pair' not in msg.lower():
                        # Directly updates the identifier
                        preprint.set_identifier_value(category='doi', value=doi)

                    dois_processed += 1

                    # Mark legacy DOIs overwritten by newly batch confirmed crossref DOIs
                    if legacy_doi:
                        legacy_doi.remove()

                elif record.get('status').lower() == 'failure':
                    if 'Relation target DOI does not exist' in record.find('msg').text:
                        logger.warning('Related publication DOI does not exist, sending metadata again without it...')
                        mint_doi_on_crossref_fail.apply_async(kwargs={'preprint_id': preprint._id})
                    # This error occurs when a single preprint is being updated several times in a row
                    # with the same metadata [#PLAT-944]. Previously this broke out of the loop when
                    # record_count == 2 (single DOI submitted twice). Now batches legitimately contain
                    # 2 records (versioned + unversioned DOI), so we continue instead of break to allow
                    # the remaining record to be processed.
                    elif 'less or equal to previously submitted version' in record.find('msg').text:
                        dois_processed += 1
                        continue
                    else:
                        unexpected_errors = True
            logger.info(f'Creation success email received from CrossRef for preprints: {guids}')

        if dois_processed != record_count or status != 'completed':
            if unexpected_errors:
                batch_id = crossref_email_content.find('batch_id').text
                email_error_text = request.POST['body-plain']
                NotificationTypeEnum.DESK_CROSSREF_ERROR.instance.emit(
                    destination_address=settings.OSF_SUPPORT_EMAIL,
                    event_context={
                        'batch_id': batch_id,
                        'email_content': request.POST['body-plain'],
                    },
                )
                logger.error(f'Error submitting metadata for batch_id {batch_id} with CrossRef, email sent to help desk: {email_error_text}')

        return HttpResponse('Mail received', status=200)
