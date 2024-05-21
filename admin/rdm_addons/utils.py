# -*- coding: utf-8 -*-

import logging
import os

from django.urls import reverse

from framework.exceptions import PermissionsError

from osf.models import RdmAddonOption, RdmAddonNoInstitutionOption
from website import settings
from admin.base.settings import BASE_DIR
from admin.rdm.utils import get_institution_id
from admin.base.settings import UNSUPPORTED_FORCE_TO_USE_ADDONS
from admin import rdm_addons


logger = logging.getLogger(__name__)


def get_institusion_settings_template(config):
    """get template file settings"""
    short_name = config.short_name
    base_path = os.path.join('rdm_addons', 'addons')

    if short_name in ['dataverse', 'owncloud', 's3', 'iqbrims',
                      'dropboxbusiness']:
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
        'is_supported_force_to_use': config.short_name not in UNSUPPORTED_FORCE_TO_USE_ADDONS,
    }
    ret.update(user_addon.to_json(user) if user_addon else {})
    return ret

def get_addons_by_config_type(config_type, user):
    """get a list of Addon objects from the Config Type of Addon."""
    addons = [addon for addon in settings.ADDONS_AVAILABLE if config_type in addon.configs and not addon.for_institutions]
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
        public_js_file = os.path.join('/', 'static', 'public', 'js', filename)
        try:
            hash_path = rdm_addons.webpack_asset(public_js_file)
        except KeyError:
            continue
        public_hash_file = public_js_file.replace(os.path.basename(public_js_file), os.path.basename(hash_path))
        if os.path.exists(os.path.join(BASE_DIR, public_hash_file.lstrip('/'))):
            js_url_list.append(hash_path)
    return js_url_list

def _get_rdm_addon_option_get_only(institution_id, addon_name):
    try:
        if institution_id:
            rdm_addon_option = RdmAddonOption.objects.get(
                institution_id=institution_id,
                provider=addon_name)
        else:
            rdm_addon_option = RdmAddonNoInstitutionOption.objects.get(
                provider=addon_name)
        return rdm_addon_option
    except Exception:
        # Since there are multiple exceptions that can be caught by this block,
        # logging at the warning level will help to identify the problem.
        logger.warning(
            'Failed to get RdmAddonOption for institution_id={}, addon_name={}'.format(institution_id, addon_name),
            exc_info=True,
        )
        return None

def _get_is_allowed_default(addon_name):
    app = settings.ADDONS_AVAILABLE_DICT.get(addon_name)
    if not app:
        # If an add-on is requested even though it is not in ADDONS_AVAILABLE_DICT, it is probably a bug on the requestor's side,
        # so output a log at the warning level.
        logger.warning('The add-on "{}" is not in ADDONS_AVAILABLE_DICT.'.format(addon_name))
        return None
    # is_allowed_default is False when for_institutions is True
    for_institutions = getattr(app, 'for_institutions', False)
    return getattr(app, 'is_allowed_default', True) and not for_institutions

def get_rdm_addon_option(institution_id, addon_name, create=True):
    """get model objects of RdmAddonOption or RdmAddonNoInstitutionOption"""
    if not create:
        return _get_rdm_addon_option_get_only(institution_id, addon_name)
    defaults = {}
    is_allowed_default = _get_is_allowed_default(addon_name)
    if is_allowed_default is not None:
        defaults['is_allowed'] = is_allowed_default

    if institution_id:
        rdm_addon_option, created = RdmAddonOption.objects.get_or_create(
            institution_id=institution_id,
            provider=addon_name,
            defaults=defaults,
        )
    else:
        rdm_addon_option, created = RdmAddonNoInstitutionOption.objects.get_or_create(
            provider=addon_name,
            defaults=defaults,
        )
    return rdm_addon_option

def update_with_rdm_addon_settings(addon_setting, user):
    """add configuration information specific to RDM to the GakuNin RDM Addon settings"""
    institutoin_id = get_institution_id(user)
    for addon in addon_setting:
        addon_name = addon['addon_short_name']
        rdm_addon_option = get_rdm_addon_option(institutoin_id, addon_name)
        addon['is_allowed'] = rdm_addon_option.is_allowed
        addon['is_forced'] = rdm_addon_option.is_forced
        addon['has_external_accounts'] = rdm_addon_option.external_accounts.exists()
        addon['has_user_external_accounts'] = user.external_accounts.filter(provider=addon_name).exists()

def validate_rdm_addons_allowed(auth, addon_name):
    institution_id = get_institution_id(auth.user)
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.is_allowed:
        raise PermissionsError('Unable to access account.\n'
                               'You are prohibited from using this add-on.')
