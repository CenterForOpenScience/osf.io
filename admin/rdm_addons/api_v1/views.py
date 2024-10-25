# -*- coding: utf-8 -*-

import json
from rest_framework import status as http_status

from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator
import flask

from osf.models import ExternalAccount, Guid, AbstractNode
from osf.utils import permissions
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_addons.utils import get_rdm_addon_option
from framework.auth import Auth

from admin.rdm_addons import utils


class OAuthView(RdmPermissionMixin, UserPassesTestMixin, View):
    """View for revoking add-on authentication information"""
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """disable CSRF"""
        return super(OAuthView, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """disconnect OAuth"""
        external_account_id = kwargs['external_account_id']
        institution_id = int(kwargs['institution_id'])
        user = self.request.user
        return disconnect(external_account_id, institution_id, user)

def disconnect(external_account_id, institution_id, user):
    """disconnect OAuth"""
    account = ExternalAccount.load(external_account_id)

    if not account:
        raise Http404

    rdm_addon_option = get_rdm_addon_option(institution_id, account.provider)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        raise Http404

    app = flask.Flask(__name__)
    with app.test_client() as c:
        # Create dummy Flask communication.
        # revoke_oauth_access method goes through flask
        # in order to confirm the user is logged in.
        c.get('/')
        # iterate AddonUserSettings for addons
        for user_settings in user.get_oauth_addons():
            if user_settings.oauth_provider.short_name == account.provider:
                user_settings.revoke_oauth_access(account, Auth(user))
                user_settings.save()

        # # only after all addons have been dealt with can we remove it from the user
        rdm_addon_option.external_accounts.remove(account)
        rdm_addon_option.save()
        user.external_accounts.remove(account)
        user.save()
    return HttpResponse('')


class SettingsView(RdmPermissionMixin, UserPassesTestMixin, View):
    """View for getting add-on configuration information"""
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        # Separate by add-on the processing to acquire settings.
        settings = get_settings(addon_name, institution_id)
        return JsonResponse(settings)

def get_settings(addon_name, institution_id):
    """get add-on configuration information."""
    if addon_name == 'dataverse':
        from addons.dataverse.settings import DEFAULT_HOSTS
        return {
            'result': {
                'userHasAuth': False,
                'urls': {
                    'create': reverse('addons:api_v1:accounts', args=[addon_name, institution_id]),
                    'accounts': reverse('addons:api_v1:accounts', args=[addon_name, institution_id])
                },
                'hosts': DEFAULT_HOSTS
            }
        }
    return {}

class AccountsView(RdmPermissionMixin, UserPassesTestMixin, View):
    """get add-on account information."""
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """disable CSRF"""
        return super(AccountsView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])

        rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
        # check existence of OAuth authentication settings
        if not rdm_addon_option.external_accounts.exists():
            res = add_extra_info({'accounts': []}, addon_name)
            return JsonResponse(res)
        accounts = []
        for external_account in rdm_addon_option.external_accounts.all():
            if external_account.provider == addon_name:
                account = {
                    'id': external_account._id,
                    'provider_id': external_account.provider_id,
                    'provider_name': external_account.provider_name,
                    'provider_short_name': external_account.provider,
                    'display_name': external_account.display_name,
                    'profile_url': external_account.profile_url,
                }
                # add each add-on's account information
                account = add_addon_extra_info(account, external_account, addon_name)
                accounts.append(account)
        res = add_extra_info({'accounts': accounts}, addon_name)
        return JsonResponse(res)

    def post(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        json_request = json.loads(request.body)
        # registration of authentication / authorization information
        response, status = add_account(json_request, institution_id, addon_name)
        return JsonResponse(response, status=status)

class ManageView(RdmPermissionMixin, UserPassesTestMixin, View):
    """View for management project of add-on"""
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """disable CSRF"""
        return super(ManageView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']

        institution_id = int(kwargs['institution_id'])
        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if rdm_addon_option.management_node is None:
            return JsonResponse({'guid': None})
        else:
            return JsonResponse({'guid': rdm_addon_option.management_node._id})

    def put(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        json_request = json.loads(request.body)
        if 'guid' not in json_request:
            return JsonResponse({
                'message': 'Require "guid" parameter.'
            }, status=http_status.HTTP_400_BAD_REQUEST)
        guid = json_request['guid']

        guid_obj = Guid.objects.get(_id=guid)
        node = guid_obj.referent
        if not isinstance(node, AbstractNode):
            return JsonResponse({
                'message': 'Invalid GUID of management project.'
            }, status=http_status.HTTP_400_BAD_REQUEST)

        if not node.has_permission(request.user, permissions.WRITE):
            return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if rdm_addon_option.management_node is not None and \
                not rdm_addon_option.management_node.has_permission(request.user, permissions.WRITE):
            return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

        rdm_addon_option.management_node = node
        rdm_addon_option.save()

        return JsonResponse({}, status=http_status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])

        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if rdm_addon_option.management_node is not None:
            if not rdm_addon_option.management_node.has_permission(request.user, permissions.WRITE):
                return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

            rdm_addon_option.management_node = None
            rdm_addon_option.save()

        return JsonResponse({}, status=http_status.HTTP_200_OK)

class OrganizationView(RdmPermissionMixin, UserPassesTestMixin, View):
    """View for organizational project of add-on"""
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """disable CSRF"""
        return super(OrganizationView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']

        institution_id = int(kwargs['institution_id'])
        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if rdm_addon_option.organizational_node is None:
            return JsonResponse({'guid': None})
        else:
            return JsonResponse({'guid': rdm_addon_option.organizational_node._id})

    def put(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        json_request = json.loads(request.body)
        if 'guid' not in json_request:
            return JsonResponse({
                'message': 'Require "guid" parameter.'
            }, status=http_status.HTTP_400_BAD_REQUEST)
        guid = json_request['guid']

        guid_obj = Guid.objects.get(_id=guid)
        node = guid_obj.referent
        if not isinstance(node, AbstractNode):
            return JsonResponse({
                'message': 'Invalid GUID of organizational project.'
            }, status=http_status.HTTP_400_BAD_REQUEST)

        if not node.has_permission(request.user, permissions.WRITE):
            return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if rdm_addon_option.organizational_node is not None and \
                not rdm_addon_option.organizational_node.has_permission(request.user, permissions.WRITE):
            return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

        rdm_addon_option.organizational_node = node
        rdm_addon_option.save()

        return JsonResponse({}, status=http_status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])

        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if rdm_addon_option.organizational_node is not None:
            if not rdm_addon_option.organizational_node.has_permission(request.user, permissions.WRITE):
                return JsonResponse({'message': 'Forbidden'}, status=http_status.HTTP_403_FORBIDDEN)

            rdm_addon_option.organizational_node = None
            rdm_addon_option.save()

        return JsonResponse({}, status=http_status.HTTP_200_OK)

def add_addon_extra_info(ret, external_account, addon_name):
    """add each add-on's account information"""
    if addon_name == 'dataverse':
        ret.update({
            'host': external_account.oauth_key,
            'host_url': 'https://{0}'.format(external_account.oauth_key),
        })
    return ret

def add_extra_info(ret, addon_name):
    """add each add-on's non-account-related individual information"""
    if addon_name == 'owncloud':
        from addons.owncloud.settings import DEFAULT_HOSTS
        ret.update({
            'hosts': DEFAULT_HOSTS
        })
    return ret

def add_account(json_request, institution_id, addon_name):
    if addon_name == 'dataverse':
        from admin.rdm_addons.api_v1.add.dataverse import add_account
        return add_account(json_request, institution_id, addon_name)
    elif addon_name == 's3':
        from admin.rdm_addons.api_v1.add.s3 import add_account
        return add_account(json_request, institution_id, addon_name)
    elif addon_name == 'owncloud':
        from admin.rdm_addons.api_v1.add.owncloud import add_account
        return add_account(json_request, institution_id, addon_name)
    elif addon_name == 'weko':
        from admin.rdm_addons.api_v1.add.weko import add_account
        return add_account(json_request, institution_id, addon_name)
    return {'message': 'unknown addon "{}"'.format(addon_name)}, http_status.HTTP_400_BAD_REQUEST
