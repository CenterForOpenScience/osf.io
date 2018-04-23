# -*- coding: utf-8 -*-

import importlib
import os
from mimetypes import MimeTypes
import uuid

import django
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.forms.models import model_to_dict
import flask

from osf.models import Institution, RdmAddonOption, OSFUser
from admin.base import settings as admin_settings
from website import settings as website_settings
from admin.rdm.utils import RdmPermissionMixin, get_dummy_institution
from . import utils
from website.routes import make_url_map
from website.app import init_addons, attach_handlers

def init_app():
    from framework.flask import app
    make_url_map(app)
    init_addons(website_settings)
    attach_handlers(app, website_settings)
    for addon in website_settings.ADDONS_AVAILABLE:
        try:
            addon.ready()
        except AssertionError:
            pass
    return app
app = init_app()

class InstitutionListView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """Institution一覧画面用のView"""
    template_name = 'rdm_addons/institution_list.html'
    raise_exception = True

    def test_func(self):
        """権限等のチェック"""
        # ログインチェック
        if not self.is_authenticated:
            return False
        # 統合管理者または機関管理者なら許可
        if self.is_super_admin or self.is_admin:
            return True
        return False

    def get(self, request, *args, **kwargs):
        """コンテキスト取得"""
        user = self.request.user
        # 統合管理者
        if self.is_super_admin:
            ctx = {
                'institutions': Institution.objects.order_by('id').all(),
                'logohost': admin_settings.OSF_URL,
            }
            return self.render_to_response(ctx)
        # 機関管理者
        elif self.is_admin:
            institution = user.affiliated_institutions.first()
            if institution:
                return redirect(reverse('addons:addons', args=[institution.id]))
            else:
                institution = get_dummy_institution()
                return redirect(reverse('addons:addons', args=[institution.id]))

class AddonListView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """アドオンの設定一覧用のView"""
    template_name = 'rdm_addons/addon_list.html'
    raise_exception = True

    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_context_data(self, **kwargs):
        """コンテキスト取得"""
        ctx = super(AddonListView, self).get_context_data(**kwargs)
        institution_id = int(kwargs['institution_id'])

        if Institution.objects.filter(pk=institution_id).exists():
            institution = Institution.objects.get(pk=institution_id)
        else:
            institution = get_dummy_institution()
        ctx['institution'] = institution

        with app.test_request_context():
            ctx['addon_settings'] = utils.get_addons_by_config_type('accounts', self.request.user)
            accounts_addons = [addon for addon in website_settings.ADDONS_AVAILABLE
                    if 'accounts' in addon.configs]
            ctx.update({
                'addon_enabled_settings': [addon.short_name for addon in accounts_addons],
                'addons_js': utils.collect_addon_js(accounts_addons),
                'addon_capabilities': website_settings.ADDON_CAPABILITIES,
                'addons_css': []
            })

            for addon in ctx['addon_settings']:
                addon_name = addon['addon_short_name']
                rdm_addon_option = utils.get_rdm_addon_option(institution.id, addon_name)
                addon['option'] = {}
                addon['option'] = model_to_dict(rdm_addon_option)
                addon['option']['external_accounts'] = rdm_addon_option.external_accounts.values()
                #print addon['option']

            return ctx

class IconView(RdmPermissionMixin, UserPassesTestMixin, View):
    """各アドオンのアイコン画像用のView"""
    raise_exception = True
    
    def test_func(self):
        """権限等のチェック"""
        # ログインチェック
        return self.is_authenticated

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        addon = utils.get_addon_config('accounts', addon_name)
        if addon:
            # アイコン画像の取得
            image_path = os.path.join('addons', addon_name, 'static', addon.icon)
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    content_type = MimeTypes().guess_type(addon.icon)[0]
                    return HttpResponse(image_data, content_type=content_type)
        raise Http404

class AddonAllowView(RdmPermissionMixin, UserPassesTestMixin, View):
    """各アドオンの使用を許可するかどうかを保存するためのView"""
    raise_exception = True
    
    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        is_allowed = bool(int(kwargs['allowed']))
        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        rdm_addon_option.is_allowed = is_allowed
        rdm_addon_option.save()
        if not is_allowed:
            self.revoke_user_accounts(institution_id, addon_name)
        return HttpResponse('')

    def revoke_user_accounts(self, institution_id, addon_name):
        """管理者が指定するクラウドストレージを利用しているプロジェクトから接続を切断する。"""
        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        if institution_id:
            users = OSFUser.objects.filter(affiliated_institutions__pk=institution_id)
        else:
            users = OSFUser.objects.filter(affiliated_institutions__isnull=True)
        if not users.exists() or not rdm_addon_option.external_accounts.exists():
            return
        accounts = rdm_addon_option.external_accounts.all()
        for user in users.all():
            for account in accounts:
                user.external_accounts.remove(account)
            user.save()

class AddonForceView(RdmPermissionMixin, UserPassesTestMixin, View):
    """各アドオンの使用を強制するかどうかを保存するためのView"""
    raise_exception = True
    
    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get(self, request, *args, **kwargs):
        addon_name = kwargs['addon_name']
        institution_id = int(kwargs['institution_id'])
        is_forced = bool(int(kwargs['forced']))
        rdm_addon_option = utils.get_rdm_addon_option(institution_id, addon_name)
        rdm_addon_option.is_forced = is_forced
        rdm_addon_option.save()
        return HttpResponse('')
