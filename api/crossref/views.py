import lxml.etree

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from api.crossref.permissions import RequestComesFromMailgun
from framework.auth.views import mails
from osf.models import PreprintService
from website import settings


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

    def post(self, request):
        crossref_email_content = lxml.etree.fromstring(str(request.POST['body-plain']))
        record_status = crossref_email_content.get('status').lower()
        batch_status = crossref_email_content.find('record_diagnostic').get('status').lower()
        preprint_guid = crossref_email_content.find('batch_id').text
        preprint = PreprintService.load(preprint_guid)

        success = record_status == 'completed' and batch_status == 'success'

        if success:
            registered_doi = crossref_email_content.find('record_diagnostic/doi').text
            preprint.set_identifier_value(doi=registered_doi)

        else:
            # If the preprint has a doi, mark it as deleted and email OSF Support
            if preprint.get_identifier_value('doi'):
                incorrect_doi = preprint.identifiers.get(category='doi')
                doi_value = incorrect_doi.value
                incorrect_doi.remove()

            mails.send_mail(
                to_addr=settings.OSF_SUPPORT_EMAIL,
                mail=mails.CROSSREF_ERROR,
                preprint=preprint,
                doi=doi_value,
                email_content=request.POST['body-plain'],
                mimetype='plain'
            )

        return HttpResponse('Mail received', status=200)
