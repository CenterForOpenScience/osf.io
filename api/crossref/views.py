import logging

import lxml.etree
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from api.crossref.permissions import RequestComesFromMailgun
from framework.auth.views import mails
from osf.models import PreprintService
from website import settings

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
        return super(ParseCrossRefConfirmation, self).dispatch(request, *args, **kwargs)

    def get_serializer_class(self):
        return None

    def post(self, request):
        crossref_email_content = lxml.etree.fromstring(str(request.POST['body-plain']))
        record_status = crossref_email_content.get('status').lower()
        batch_status = crossref_email_content.find('record_diagnostic').get('status').lower()
        preprint_guid = crossref_email_content.find('batch_id').text
        preprint = PreprintService.load(preprint_guid)
        registered_doi = crossref_email_content.find('record_diagnostic/doi').text
        message = crossref_email_content.find('record_diagnostic/msg').text.lower()

        record_count = crossref_email_content.find('batch_data/record_count').text

        success = record_status == 'completed' and batch_status == 'success'
        updated = success and message == 'successfully updated'

        if not preprint and record_count > 1:
            logger.info('No preprint with this GUID could be found, perhaps it is a batch update!')
        else:
            # Set the DOI on the preprint if this is not just a metadata update
            if success and not updated:
                logger.info('Success email recieved from CrossRef for preprint {}'.format())
                if not preprint.get_identifier_value('doi'):
                    preprint.set_identifier_value(category='doi', value=registered_doi)

            elif updated:
                logger.info('Metadata for preprint {} successfully updated with CrossRef'.format(preprint_guid))

            else:
                logger.error('Error submitting metdata for preprint {} with CrossRef, email sent to help desk'.format(preprint_guid))
                mails.send_mail(
                    to_addr=settings.OSF_SUPPORT_EMAIL,
                    mail=mails.CROSSREF_ERROR,
                    preprint=preprint,
                    doi=registered_doi or settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id),
                    email_content=request.POST['body-plain'],
                )

        return HttpResponse('Mail received', status=200)
