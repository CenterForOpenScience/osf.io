# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.views.generic import TemplateView
import hashlib
import json

from addons.osfstorage.models import Region
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import csl_utils
from osf.models import Institution
from scripts import refresh_addon_tokens

SITE_KEY = 'rdm_custom_storage_location'


def external_acc_update(request, **kwargs):
    access_token = kwargs.get('access_token')
    if hashlib.sha512(SITE_KEY).hexdigest() == access_token.lower():
        refresh_addon_tokens.run_main({'googledrive': 14}, (5, 1), False)
    else:
        response_hash = {'state': 'fail', 'error': 'access forbidden'}
        response_json = json.dumps(response_hash)
        response = HttpResponse(response_json, content_type='application/json')
        return response
    return HttpResponse('Done')


class InstitutionalStorage(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    model = Institution
    template_name = 'rdm_custom_storage_location/institutional_storage.html'

    def test_func(self):
        """check user permissions"""
        return not self.is_super_admin and self.is_admin and \
            self.request.user.affiliated_institutions.exists()

    def get_context_data(self, *args, **kwargs):
        institution = self.request.user.affiliated_institutions.first()

        region = None
        if Region.objects.filter(_id=institution._id).exists():
            region = Region.objects.get(_id=institution._id)
        else:
            region = Region.objects.first()

        kwargs['region'] = region
        kwargs['addons'] = csl_utils.get_addons()
        kwargs['provider'] = csl_utils.get_provider_short_name(region.waterbutler_settings)
        return kwargs
