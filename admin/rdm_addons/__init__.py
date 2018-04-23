# -*- coding: utf-8 -*-

from django.template.defaultfilters import register
from website.util.paths import webpack_asset as _webpack_asset

@register.filter(is_safe=True)
def render_user_settings_template(addon):
    tmpl = addon['user_settings_template']
    return tmpl.render(**addon)

@register.filter(is_safe=True)
def webpack_asset(path):
    return _webpack_asset(path)

@register.filter
def external_account_id(account):
    return account['_id']