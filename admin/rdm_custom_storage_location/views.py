# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse, Http404, JsonResponse
from django.views.generic import TemplateView, View
import json
import hashlib
from rest_framework import status as http_status
from mimetypes import MimeTypes
import os
import csv
from io import StringIO
import logging

from addons.osfstorage.models import Region
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location import utils
from osf.models import Institution, OSFUser
from osf.models.external import ExternalAccountTemporary
from scripts import refresh_addon_tokens
from website import settings as osf_settings
from distutils.util import strtobool

logger = logging.getLogger(__name__)

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
        kwargs['osf_domain'] = osf_settings.DOMAIN
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
            return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

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
        elif provider_short_name == 's3compatb3':
            result = utils.test_s3compatb3_connection(
                data.get('s3compatb3_endpoint_url'),
                data.get('s3compatb3_access_key'),
                data.get('s3compatb3_secret_key'),
                data.get('s3compatb3_bucket'),
            )
        elif provider_short_name == 's3compatinstitutions':
            result = utils.test_s3compat_connection(
                data.get('s3compatinstitutions_endpoint_url'),
                data.get('s3compatinstitutions_access_key'),
                data.get('s3compatinstitutions_secret_key'),
                data.get('s3compatinstitutions_bucket'),
            )
        elif provider_short_name == 'ociinstitutions':
            result = utils.test_s3compatb3_connection(
                data.get('ociinstitutions_endpoint_url'),
                data.get('ociinstitutions_access_key'),
                data.get('ociinstitutions_secret_key'),
                data.get('ociinstitutions_bucket'),
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
            result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)

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
            return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

        storage_name = data.get('storage_name')
        if not storage_name and utils.have_storage_name(provider_short_name):
            return JsonResponse({
                'message': 'Storage name is missing.'
            }, status=http_status.HTTP_400_BAD_REQUEST)

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
                bool(strtobool(data.get('s3compat_server_side_encryption'))),
            )
        elif provider_short_name == 's3compatb3':
            result = utils.save_s3compatb3_credentials(
                institution_id,
                storage_name,
                data.get('s3compatb3_endpoint_url'),
                data.get('s3compatb3_access_key'),
                data.get('s3compatb3_secret_key'),
                data.get('s3compatb3_bucket'),
            )
        elif provider_short_name == 's3compatinstitutions':
            result = utils.save_s3compatinstitutions_credentials(
                institution,
                storage_name,
                data.get('s3compatinstitutions_endpoint_url'),
                data.get('s3compatinstitutions_access_key'),
                data.get('s3compatinstitutions_secret_key'),
                data.get('s3compatinstitutions_bucket'),
                provider_short_name,
            )
        elif provider_short_name == 'ociinstitutions':
            result = utils.save_ociinstitutions_credentials(
                institution,
                storage_name,
                data.get('ociinstitutions_endpoint_url'),
                data.get('ociinstitutions_access_key'),
                data.get('ociinstitutions_secret_key'),
                data.get('ociinstitutions_bucket'),
                provider_short_name,
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
                storage_name,
                data.get('nextcloudinstitutions_host'),
                data.get('nextcloudinstitutions_username'),
                data.get('nextcloudinstitutions_password'),
                data.get('nextcloudinstitutions_folder'),  # base folder
                data.get('nextcloudinstitutions_notification_secret'),
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
                institution,
                storage_name,
                provider_short_name)
        elif provider_short_name == 'onedrivebusiness':
            result = utils.save_onedrivebusiness_credentials(
                request.user,
                storage_name,
                provider_short_name,
                data.get('onedrivebusiness_folder'),
            )
        else:
            result = ({'message': 'Invalid provider.'}, http_status.HTTP_400_BAD_REQUEST)
        status = result[1]
        if status == http_status.HTTP_200_OK:
            utils.change_allowed_for_institutions(
                institution, provider_short_name)
        return JsonResponse(result[0], status=status)


class FetchCredentialsView(InstitutionalStorageBaseView, View):
    def _common(self, request, data):
        institution = request.user.affiliated_institutions.first()
        provider_short_name = data.get('provider_short_name')
        if not provider_short_name:
            response = {
                'message': 'Provider is missing.'
            }
            return JsonResponse(response, status=http_status.HTTP_400_BAD_REQUEST)

        result = None
        data = None
        if provider_short_name == 'nextcloudinstitutions':
            data = utils.get_nextcloudinstitutions_credentials(institution)
        elif provider_short_name == 's3compatinstitutions':
            data = utils.get_s3compatinstitutions_credentials(institution)
        elif provider_short_name == 'ociinstitutions':
            data = utils.get_ociinstitutions_credentials(institution)
        else:
            result = ({'message': 'unsupported'}, http_status.HTTP_400_BAD_REQUEST)

        if data:
            result = (data, http_status.HTTP_200_OK)
        elif not result:
            result = ({'message': 'no credentials'}, http_status.HTTP_400_BAD_REQUEST)

        return JsonResponse(result[0], status=result[1])

    def post(self, request):
        data = json.loads(request.body)
        return self._common(request, data)

    def get(self, request):
        return self._common(request, request.GET)


class FetchTemporaryTokenView(InstitutionalStorageBaseView, View):
    def post(self, request):
        data = json.loads(request.body)
        provider_short_name = data.get('provider_short_name')

        if not provider_short_name:
            return JsonResponse({
                'message': 'Provider is missing.'
            }, status=http_status.HTTP_400_BAD_REQUEST)

        institution_id = request.user.affiliated_institutions.first()._id
        data = utils.get_oauth_info_notification(institution_id, provider_short_name)
        if data:
            data['fullname'] = request.user.fullname
            return JsonResponse({
                'response_data': data
            }, status=http_status.HTTP_200_OK)

        return JsonResponse({
            'message': 'Oauth permission procedure was canceled'
        }, status=http_status.HTTP_400_BAD_REQUEST)


class RemoveTemporaryAuthData(InstitutionalStorageBaseView, View):
    def post(self, request):
        institution_id = request.user.affiliated_institutions.first()._id
        ExternalAccountTemporary.objects.filter(_id=institution_id).delete()
        return JsonResponse({
            'message': 'Garbage data removed!!'
        }, status=http_status.HTTP_200_OK)

def external_acc_update(request, access_token):
    if hashlib.sha512(SITE_KEY.encode('utf-8')).hexdigest() != access_token.lower():
        return HttpResponse(
            json.dumps({'state': 'fail', 'error': 'access forbidden'}),
            content_type='application/json',
        )

    refresh_addon_tokens.run_main(
        addons={'googledrive': -14, 'box': -14},
        dry_run=False
    )
    return HttpResponse('Done')


def to_bool(val):
    return val.lower() in ['true']

class UserMapView(InstitutionalStorageBaseView, View):
    def post(self, request, *args, **kwargs):
        provider_name = request.POST.get('provider', None)
        institution = request.user.affiliated_institutions.first()

        OK = 'OK'
        NG = 'NG'
        clear = to_bool(request.POST.get('clear', 'false'))
        if clear:
            utils.clear_usermap_tmp(provider_name, institution)
            return JsonResponse({
                OK: 0,
                NG: 0,
                'provider_name': provider_name,
                'report': [],
                'user_to_extuser': {},
            }, status=http_status.HTTP_200_OK)

        check_extuser = to_bool(request.POST.get('check_extuser', 'false'))
        usermap = request.FILES['usermap']
        csv_reader = csv.reader(usermap, delimiter=',', quotechar='"')

        result = {OK: 0, NG: 0}
        user_to_extuser = dict()  # This is UserMap.  (guid -> extuser)
        extuser_set = set()
        report = []
        INVALID_FORMAT = 'INVALID_FORMAT'
        EMPTY_USER = 'EMPTY_USER'
        EMPTY_EXTUSER = 'EMPTY_EXTUSER'
        UNKNOWN_USER = 'UNKNOWN_USER'
        UNKNOWN_EXTUSER = 'UNKNOWN_EXTUSER'
        DUPLICATED_USER = 'DUPLICATED_USER'
        DUPLICATED_EXTUSER = 'DUPLICATED_EXTUSER'

        MAX_NG = 20

        def add_report(status, reason, line, detail=None):
            result[status] += 1
            if status == NG and result[NG] >= MAX_NG:
                return
            try:
                joined = ','.join(line).decode('utf-8')
            except Exception:
                joined = ''
            if status == OK:
                # OK is not reported.
                # report.append(u'{}: {}'.format(status, joined))
                pass
            elif detail:
                report.append(u'{}, {} ({}): {}'.format(status, reason, detail, joined))
            else:
                report.append(u'{}, {}: {}'.format(status, reason, joined))

        try:
            for line in csv_reader:
                if len(line) == 0:
                    continue
                user = line[0].strip()
                if user.startswith('#'):
                    continue
                if len(line) != 3:
                    add_report(NG, INVALID_FORMAT, line)
                    continue
                extuser = line[1].strip()
                # optional_info = line[2].strip()

                if not user:
                    add_report(NG, EMPTY_USER, line)
                    continue
                if not extuser:
                    add_report(NG, EMPTY_EXTUSER, line)
                    continue

                # ePPN or GUID ?
                if '@' in user:  # ePPN
                    try:
                        u = OSFUser.objects.get(eppn=user)
                    except Exception:
                        u = None
                elif user:  # GUID
                    u = OSFUser.load(user.lower())
                if not u:
                    add_report(NG, UNKNOWN_USER, line)
                    continue
                if check_extuser:
                    detail = utils.extuser_exists(provider_name, request.POST,
                                                  extuser)
                    if detail:
                        add_report(NG, UNKNOWN_EXTUSER, line, detail)
                        continue

                if u._id in user_to_extuser:
                    add_report(NG, DUPLICATED_USER, line)
                    continue
                if extuser in extuser_set:
                    add_report(NG, DUPLICATED_EXTUSER, line)
                    continue
                user_to_extuser[u._id] = extuser   # guid.lower() -> extuser
                extuser_set.add(extuser)
                add_report(OK, None, line)
        except Exception as e:
            add_report(NG, INVALID_FORMAT, [str(e)])

        if result[NG] > 0:
            status = http_status.HTTP_400_BAD_REQUEST
            utils.clear_usermap_tmp(provider_name, institution)
        else:
            status = http_status.HTTP_200_OK
            utils.save_usermap_to_tmp(provider_name, institution,
                                      user_to_extuser)

        return JsonResponse({
            OK: result[OK],
            NG: result[NG],
            'provider_name': provider_name,
            'report': report,
            'user_to_extuser': user_to_extuser,
        }, status=status)

    def get(self, request, *args, **kwargs):
        # download CSV (or Templates when User mapping file is not set)
        provider_name = request.GET['provider']
        institution = request.user.affiliated_institutions.first()
        ext = 'csv'
        name = 'usermap-' + provider_name

        s = StringIO.StringIO()
        csv_writer = csv.writer(s, delimiter=',')

        def fullname(osfuser):
            fullname = osfuser.fullname
            if fullname:
                return fullname.encode('utf-8')
            return None

        header = ['#' + 'User_GUID(or ePPN)', 'External_UserID', 'Fullname(ignored)']

        # GUID -> extuser
        usermap = utils.get_usermap(provider_name, institution)

        csv_writer.writerow(header)
        if usermap:
            for guid, extuser in usermap.items():
                guid = guid.lower()
                u = OSFUser.load(guid)
                if u:
                    csv_writer.writerow([guid.upper(), extuser, fullname(u)])

        nomap_count = 0
        # find osfusers in usermap who has no mapping.
        for u in institution.osfuser_set.filter(is_active=True):
            guid = u._id
            if usermap is None or guid not in usermap:
                nomap_count += 1
                if nomap_count == 1:
                    if usermap:
                        csv_writer.writerow([])
                    csv_writer.writerow(['#' + 'Please input External users into the second column.'])
                csv_writer.writerow([guid.upper(), None, fullname(u)])

        resp = HttpResponse(s.getvalue(), content_type='text/%s' % ext)
        resp['Content-Disposition'] = 'attachment; filename=%s.%s' % (name, ext)
        return resp
