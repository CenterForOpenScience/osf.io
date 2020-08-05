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
from osf.models.external import ExternalAccountTemporary
from scripts import refresh_addon_tokens

SITE_KEY = 'rdm_custom_storage_location'

class InstitutionalStorageBaseView(RdmPermissionMixin, UserPassesTestMixin):
    """ Base class for all the Institutional Storage Views """
    def test_func(self):
        """ Check user permissions """
        return not self.is_super_admin and self.is_admin and \
            self.request.user.affiliated_institutions.exists()


class InstitutionalStorageView(InstitutionalStorageBaseView, TemplateView):
    """ View that shows the Institutional Storage's template """
    model = Institution
    template_name = 'rdm_custom_storage_location/institutional_storage.html'

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
        kwargs['have_storage_name'] = utils.have_storage_name(provider_name)
        return kwargs


class IconView(InstitutionalStorageBaseView, View):
    """ View for each addon's icon """
    raise_exception = True

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


class TestConnectionView(InstitutionalStorageBaseView, View):
    """ View for testing the credentials to connect to a provider.
    Called when clicking the 'Connect' Button.
    """
    def post(self, request):
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
                data.get('s3_secret_key'),
                data.get('s3_bucket'),
            )
        elif provider_short_name == 's3compat':
            result = utils.test_s3compat_connection(
                data.get('s3compat_endpoint_url'),
                data.get('s3compat_access_key'),
                data.get('s3compat_secret_key'),
                data.get('s3compat_bucket'),
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
        elif provider_short_name == 'nextcloudinstitutions':
            result = utils.test_owncloud_connection(
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),
                provider_short_name,
            )
        elif provider_short_name == 'swift':
            result = utils.test_swift_connection(
                data.get('swift_auth_version'),
                data.get('swift_auth_url'),
                data.get('swift_access_key'),
                data.get('swift_secret_key'),
                data.get('swift_tenant_name'),
                data.get('swift_user_domain_name'),
                data.get('swift_project_domain_name'),
                data.get('swift_container'),
            )
        elif provider_short_name == 'dropboxbusiness':
            institution = request.user.affiliated_institutions.first()
            result = utils.test_dropboxbusiness_connection(institution)

        else:
            result = ({'message': 'Invalid provider.'}, httplib.BAD_REQUEST)

        return JsonResponse(result[0], status=result[1])


class SaveCredentialsView(InstitutionalStorageBaseView, View):
    """ View for saving the credentials to the provider into the database.
    Called when clicking the 'Save' Button.
    """
    def post(self, request):
        institution = request.user.affiliated_institutions.first()
        institution_id = institution._id
        data = json.loads(request.body)

        provider_short_name = data.get('provider_short_name')
        if not provider_short_name:
            response = {
                'message': 'Provider is missing.'
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        storage_name = data.get('storage_name')
        if not storage_name and utils.have_storage_name(provider_short_name):
            return JsonResponse({
                'message': 'Storage name is missing.'
            }, status=httplib.BAD_REQUEST)

        result = None

        if provider_short_name == 's3':
            result = utils.save_s3_credentials(
                institution_id,
                storage_name,
                data.get('s3_access_key'),
                data.get('s3_secret_key'),
                data.get('s3_bucket'),
            )
        elif provider_short_name == 's3compat':
            result = utils.save_s3compat_credentials(
                institution_id,
                storage_name,
                data.get('s3compat_endpoint_url'),
                data.get('s3compat_access_key'),
                data.get('s3compat_secret_key'),
                data.get('s3compat_bucket'),
            )
        elif provider_short_name == 'swift':
            result = utils.save_swift_credentials(
                institution_id,
                storage_name,
                data.get('swift_auth_version'),
                data.get('swift_access_key'),
                data.get('swift_secret_key'),
                data.get('swift_tenant_name'),
                data.get('swift_user_domain_name'),
                data.get('swift_project_domain_name'),
                data.get('swift_auth_url'),
                data.get('swift_container'),
            )
        elif provider_short_name == 'osfstorage':
            result = utils.save_osfstorage_credentials(
                institution_id,
            )
        elif provider_short_name == 'googledrive':
            result = utils.save_googledrive_credentials(
                request.user,
                storage_name,
                data.get('googledrive_folder'),
            )
        elif provider_short_name == 'owncloud':
            result = utils.save_owncloud_credentials(
                institution_id,
                storage_name,
                data.get('owncloud_host'),
                data.get('owncloud_username'),
                data.get('owncloud_password'),
                data.get('owncloud_folder'),
                'owncloud'
            )
        elif provider_short_name == 'nextcloud':
            result = utils.save_nextcloud_credentials(
                institution_id,
                storage_name,
                data.get('nextcloud_host'),
                data.get('nextcloud_username'),
                data.get('nextcloud_password'),
                data.get('nextcloud_folder'),
                'nextcloud',
            )
        elif provider_short_name == 'nextcloudinstitutions':
            result = utils.save_nextcloudinstitutions_credentials(
                institution,
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),  # base folder
                provider_short_name,
            )
        elif provider_short_name == 'box':
            result = utils.save_box_credentials(
                request.user,
                storage_name,
                data.get('box_folder'),
            )
        elif provider_short_name == 'dropboxbusiness':
            result = utils.save_dropboxbusiness_credentials(
                institution, provider_short_name)
        else:
            result = ({'message': 'Invalid provider.'}, httplib.BAD_REQUEST)
        status = result[1]
        if status == httplib.OK:
            utils.change_allowed_for_institutions(
                institution, provider_short_name)
        return JsonResponse(result[0], status=status)


class FetchCredentialsView(InstitutionalStorageBaseView, View):
    def post(self, request):
        institution = request.user.affiliated_institutions.first()
        data = json.loads(request.body)

        provider_short_name = data.get('provider_short_name')
        if not provider_short_name:
            response = {
                'message': 'Provider is missing.'
            }
            return JsonResponse(response, status=httplib.BAD_REQUEST)

        storage_name = data.get('storage_name')
        if not storage_name and utils.have_storage_name(provider_short_name):
            return JsonResponse({
                'message': 'Storage name is missing.'
            }, status=httplib.BAD_REQUEST)

        result = None
        if provider_short_name == 'nextcloudinstitutions':
            data = utils.get_nextcloudinstitutions_credentials(institution)
            result = (data, httplib.OK)

        return JsonResponse(result[0], status=result[1])


class FetchTemporaryTokenView(InstitutionalStorageBaseView, View):
    def post(self, request):
        data = json.loads(request.body)
        provider_short_name = data.get('provider_short_name')

        if not provider_short_name:
            return JsonResponse({
                'message': 'Provider is missing.'
            }, status=httplib.BAD_REQUEST)

        institution_id = request.user.affiliated_institutions.first()._id
        data = utils.get_oauth_info_notification(institution_id, provider_short_name)
        if data:
            data['fullname'] = request.user.fullname
            return JsonResponse({
                'response_data': data
            }, status=httplib.OK)

        return JsonResponse({
            'message': 'Oauth permission procedure was canceled'
        }, status=httplib.BAD_REQUEST)


class RemoveTemporaryAuthData(InstitutionalStorageBaseView, View):
    def post(self, request):
        institution_id = request.user.affiliated_institutions.first()._id
        ExternalAccountTemporary.objects.filter(_id=institution_id).delete()
        return JsonResponse({
            'message': 'Garbage data removed!!'
        }, status=httplib.OK)

def external_acc_update(request, access_token):
    if hashlib.sha512(SITE_KEY).hexdigest() != access_token.lower():
        return HttpResponse(
            json.dumps({'state': 'fail', 'error': 'access forbidden'}),
            content_type='application/json',
        )

    refresh_addon_tokens.run_main(
        addons={'googledrive': -14, 'box': -14},
        dry_run=False
    )
    return HttpResponse('Done')
