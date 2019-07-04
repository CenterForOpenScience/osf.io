# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse, Http404, JsonResponse
from django.views.generic import TemplateView, View
import json
import hashlib
import httplib
from mimetypes import MimeTypes
import os

from addons.osfstorage.models import Region
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
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
            region.name = ''

        provider_name = region.waterbutler_settings['storage']['provider']
        provider_name = provider_name if provider_name != 'filesystem' else 'osfstorage'

        kwargs['institution'] = institution
        kwargs['region'] = region
        kwargs['providers'] = utils.get_providers()
        kwargs['selected_provider_short_name'] = provider_name
        return kwargs


class IconView(RdmPermissionMixin, UserPassesTestMixin, View):
    """View for each addon's icon"""
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        return self.is_authenticated

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        addon = utils.get_addon_by_name(addon_name)
        if addon:
            # get addon's icon
            image_path = os.path.join('addons', addon_name, 'static', addon.icon)
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    content_type = MimeTypes().guess_type(addon.icon)[0]
                    return HttpResponse(image_data, content_type=content_type)
        raise Http404

def test_connection(request):
    data = json.loads(request.body)
    provider_short_name = data.get('provider_short_name', None)
    if not provider_short_name:
        response = {
            'message': 'Provider is missing.'
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)

    if provider_short_name == 's3':
        s3_access_key = data.get('s3_access_key', None)
        s3_secret_key = data.get('s3_secret_key', None)
        return utils.test_s3_connection(s3_access_key, s3_secret_key)
    elif provider_short_name == 'owncloud':
        return utils.test_owncloud_connection(
            data.get('owncloud_host'),
            data.get('owncloud_username'),
            data.get('owncloud_password'),
            data.get('owncloud_folder'),
            provider_short_name,
        )
    elif provider_short_name == 'nextcloud':
        return utils.test_owncloud_connection(
            data.get('nextcloud_host'),
            data.get('nextcloud_username'),
            data.get('nextcloud_password'),
            data.get('nextcloud_folder'),
            provider_short_name,
        )
    elif provider_short_name == 'swift':
        return utils.test_swift_connection(
            data.get('swift_auth_version'),
            data.get('swift_auth_url'),
            data.get('swift_access_key'),
            data.get('swift_secret_key'),
            data.get('swift_tenant_name'),
            data.get('swift_user_domain_name', None),
            data.get('swift_project_domain_name', None),
            data.get('swift_folder', None),
            data.get('swift_container', None),
        )

    return JsonResponse({
        'message': 'Invalid provider.'
    }, status=httplib.BAD_REQUEST)
