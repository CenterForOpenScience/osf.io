# -*- coding: utf-8 -*-

import os

from django.urls import reverse

from osf.models import RdmAddonOption, RdmAddonNoInstitutionOption
from website import settings
from admin.base.settings import BASE_DIR
from admin.rdm.utils import get_institution_id

def get_institusion_settings_template(config):
    """get template file settings"""
    short_name = config.short_name
    base_path = os.path.join('rdm_addons', 'addons')

    if short_name in ['dataverse', 'owncloud', 's3']:
        return os.path.join(base_path, '{}_institution_settings.html'.format(short_name))
    return os.path.join(base_path, 'institution_settings_default.html')

def get_addon_template_config(config, user):
    """get addons template config"""
    user_addon = user.get_addon(config.short_name)
    ret = {
        'addon_short_name': config.short_name,
        'addon_full_name': config.full_name,
        'institution_settings_template': get_institusion_settings_template(config),
        'is_enabled': user_addon is not None,
        'addon_icon_url': reverse('addons:icon', args=[config.short_name, config.icon]),
    }
    ret.update(user_addon.to_json(user) if user_addon else {})
    return ret

def get_addons_by_config_type(config_type, user):
    """get a list of Addon objects from the Config Type of Addon."""
    addons = [addon for addon in settings.ADDONS_AVAILABLE if config_type in addon.configs]
    return [get_addon_template_config(addon_config, user) for addon_config in sorted(addons, key=lambda cfg: cfg.full_name.lower())]

def get_addon_config(config_type, addon_short_name):
    """get Addon object from Short Name and Config Type of Addon."""
    for addon in settings.ADDONS_AVAILABLE:
        if config_type in addon.configs and addon.short_name == addon_short_name:
            return addon
    return None

def collect_addon_js(addons):
    """Get a list of addon's JavaScript files."""
    js_url_list = []
    for addon in addons:
        filename = 'rdm-{}-cfg.js'.format(addon.short_name)
        public_js_file = os.path.join(BASE_DIR, 'static', 'public', 'js', filename)
        if os.path.exists(public_js_file):
            js_url = '/static/public/js/{}'.format(filename)
            js_url_list.append(js_url)
    return js_url_list

def get_rdm_addon_option(institution_id, addon_name):
    """get model objects of RdmAddonOption or RdmAddonNoInstitutionOption"""
    if institution_id:
        rdm_addon_option, _ = RdmAddonOption.objects.get_or_create(institution_id=institution_id,
            provider=addon_name)
    else:
        rdm_addon_option, _ = RdmAddonNoInstitutionOption.objects.get_or_create(provider=addon_name)
    return rdm_addon_option

def update_with_rdm_addon_settings(addon_setting, user):
    """add configuration information specific to RDM to the OSF Addon settings"""
    institutoin_id = get_institution_id(user)
    for addon in addon_setting:
        addon_name = addon['addon_short_name']
        rdm_addon_option = get_rdm_addon_option(institutoin_id, addon_name)
        addon['is_allowed'] = rdm_addon_option.is_allowed
        addon['is_forced'] = rdm_addon_option.is_forced
        addon['has_external_accounts'] = rdm_addon_option.external_accounts.exists()
        addon['has_user_external_accounts'] = user.external_accounts.filter(provider=addon_name).exists()
