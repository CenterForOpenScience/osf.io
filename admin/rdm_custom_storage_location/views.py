# -*- coding: utf-8 -*-

from django.core.exceptions import PermissionDenied
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
    if request.user.is_superuser or not request.user.is_staff or \
            not request.user.affiliated_institutions.exists():
        raise PermissionDenied

    data = json.loads(request.body)

    provider_short_name = data.get('provider_short_name')
    if not provider_short_name:
        response = {
            'message': 'Provider is missing.'
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)

    result = None

    if provider_short_name == 's3':
        result = utils.test_s3_connection(
            data.get('s3_access_key'),
            data.get('s3_secret_key')
        )
    elif provider_short_name == 'owncloud':
        result = utils.test_owncloud_connection(
            data.get('owncloud_host'),
            data.get('owncloud_username'),
            data.get('owncloud_password'),
            data.get('owncloud_folder'),
            provider_short_name,
        )
    elif provider_short_name == 'nextcloud':
        result = utils.test_owncloud_connection(
            data.get('nextcloud_host'),
            data.get('nextcloud_username'),
            data.get('nextcloud_password'),
            data.get('nextcloud_folder'),
            provider_short_name,
        )
    elif provider_short_name == 'swift':
        result = utils.test_swift_connection(
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
    else:
        result = ({'message': 'Invalid provider.'}, httplib.BAD_REQUEST)

    return JsonResponse(result[0], status=result[1])

def save_credentials(request):
    if request.user.is_superuser or not request.user.is_staff or \
            not request.user.affiliated_institutions.exists():
        raise PermissionDenied

    institution_id = request.user.affiliated_institutions.first()._id
    data = json.loads(request.body)

    provider_short_name = data.get('provider_short_name')
    if not provider_short_name:
        response = {
            'message': 'Provider is missing.'
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)

    result = None

    if provider_short_name == 's3':
        result = utils.save_s3_credentials(
            institution_id,
            data.get('storage_name'),
            data.get('s3_access_key'),
            data.get('s3_secret_key'),
            data.get('s3_bucket'),
        )
    elif provider_short_name == 'swift':
        result = utils.save_swift_credentials(
            institution_id,
            data.get('storage_name'),
            data.get('swift_auth_version'),
            data.get('swift_access_key'),
            data.get('swift_secret_key'),
            data.get('swift_tenant_name'),
            data.get('swift_user_domain_name'),
            data.get('swift_project_domain_name'),
            data.get('swift_auth_url'),
            data.get('swift_folder'),
            data.get('swift_container'),
        )
    elif provider_short_name == 'osfstorage':
        result = utils.save_osfstorage_credentials(
            institution_id,
        )
    elif provider_short_name == 'googledrive':
        result = utils.save_googledrive_credentials(
            request.user,
            data.get('storage_name', None),
            data.get('provider_short_name', None),
            data.get('googledrive_folder', None),
        )
    elif provider_short_name == 'owncloud':
        result = utils.save_owncloud_credentials(
            institution_id,
            data.get('storage_name'),
            data.get('owncloud_host'),
            data.get('owncloud_username'),
            data.get('owncloud_password'),
            data.get('owncloud_folder'),
            'owncloud'
        )
    else:
        result = ({'message': 'Invalid provider.'}, httplib.BAD_REQUEST)
    from pprint import pprint
    pprint(result)
    return JsonResponse(result[0], status=result[1])

def fetch_temporary_token(request):
    if request.user.is_superuser or not request.user.is_staff or \
            not request.user.affiliated_institutions.exists():
        raise PermissionDenied

    data = json.loads(request.body)
    provider_short_name = data.get('provider_short_name', None)
    if not provider_short_name:
        response = {
            'message': 'Provider is missing.'
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)
    institution_id = request.user.affiliated_institutions.first().id
    data = utils.get_oauth_info_notification(institution_id, provider_short_name)
    if data:
        data['fullname'] = request.user.fullname
        return JsonResponse({
            'response_data': data
        }, status=httplib.OK)
    else:
        response = {
            'message': 'Oauth permission procedure was canceled'
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)

def auth_save(request):
    if request.user.is_superuser or not request.user.is_staff or \
            not request.user.affiliated_institutions.exists():
        raise PermissionDenied

    data = json.loads(request.body)
    provider_short_name = data.get('provider_short_name', None)
    if not provider_short_name:
        response = {
            'message': 'Provider is missing.'
        }
        return JsonResponse(response, status=httplib.BAD_REQUEST)
    institution_id = request.user.affiliated_institutions.first().id
    return utils.save_auth_credentials(institution_id, provider_short_name, request.user)
