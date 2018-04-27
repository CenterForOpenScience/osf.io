import lxml.etree

from rest_framework import permissions
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from framework.auth.oauth_scopes import CoreScopes
from framework.auth.views import mails
from osf.models import PreprintService
from website import settings


class ParseCrossRefConfirmation(JSONAPIBaseView):
    # This view goes under the _/ namespace
    view_name = 'parse_crossref_confirmation_email'

    permission_classes = (
        base_permissions.TokenHasScope,
        permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(ParseCrossRefConfirmation, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        crossref_email_content = lxml.etree.fromstring(str(request.POST['body-plain']))
        status = crossref_email_content.find('record_diagnostic').get('status')

        if status.lower() == 'failure':
            preprint_guid = crossref_email_content.find('batch_id').text
            preprint = PreprintService.load(preprint_guid)

            # If a DOI seems like it was successful, undo that and email OSF Support
            if preprint.get_identifier_value('doi'):

                # Remove that DOI relationship, as it's not really registered
                preprint.identifiers.get(category='doi').delete()

                mails.send_mail(
                    to_addr=settings.OSF_SUPPORT_EMAIL,
                    mail=mails.CROSSREF_ERROR,
                    preprint=preprint,
                    mimetype='plain'
                )

        return JsonResponse({'status': 'received'}, status=200)
