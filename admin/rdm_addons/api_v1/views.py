# -*- coding: utf-8 -*-

import json
import httplib

from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator
import flask

from osf.models import ExternalAccount
from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_addons.utils import get_rdm_addon_option
from framework.auth import Auth


class OAuthView(RdmPermissionMixin, UserPassesTestMixin, View):
    """アドオンの認証情報を解除するためのView"""
    raise_exception = True

    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """CSRF無効化"""
        return super(OAuthView, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """OAuth切断"""
        external_account_id = kwargs['external_account_id']
        institution_id = int(kwargs['institution_id'])
        user = self.request.user
        return disconnect(external_account_id, institution_id, user)

def disconnect(external_account_id, institution_id, user):
    """OAuthを切断する。"""
    account = ExternalAccount.load(external_account_id)

    if not account:
        raise Http404

    rdm_addon_option = get_rdm_addon_option(institution_id, account.provider)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        raise Http404

    app = flask.Flask(__name__)
    with app.test_client() as c:
        # flaskのダミーの通信を作成。
        # revoke_oauth_accessメソッドがflaskを通じて
        # ログイン済みであるかを確認しているため。
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
    """アドオンの設定情報取得用のView"""
    raise_exception = True

    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        # アドオンごとに設定情報を取得する処理を分ける。
        settings = get_settings(addon_name, institution_id)
        return JsonResponse(settings)

def get_settings(addon_name, institution_id):
    """アドオンの設定情報を取得する。"""
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
    """アドオンのアカウント情報を取得する。"""
    raise_exception = True

    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """CSRF無効化"""
        return super(AccountsView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])

        rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
        # OAuth認証の設定情報の有無の確認
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
                # アドオン固有のアカウント情報を追加する。
                account = add_addon_extra_info(account, external_account, addon_name)
                accounts.append(account)
        res = add_extra_info({'accounts': accounts}, addon_name)
        return JsonResponse(res)

    def post(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        json_request = json.loads(request.body)
        # 認証・認可情報の登録
        response, status = add_account(json_request, institution_id, addon_name)
        return JsonResponse(response, status=status)

def add_addon_extra_info(ret, external_account, addon_name):
    """アドオン固有のアカウント情報を追加する。"""
    if addon_name == 'dataverse':
        ret.update({
            'host': external_account.oauth_key,
            'host_url': 'https://{0}'.format(external_account.oauth_key),
        })
    return ret

def add_extra_info(ret, addon_name):
    """アカウント以外のアドオン固有の情報を追加する。"""
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
    return {'message': 'unknown addon "{}"'.format(addon_name)}, httplib.BAD_REQUEST
