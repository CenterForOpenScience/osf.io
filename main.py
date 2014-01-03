#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil

from framework import app

from website import settings
from website.addons.base import init_addon
from website.app import init_app
from website.project.model import ensure_schemas

# TODO: Move to settings.py
settings.ADDONS_REQUESTED = [
    'wiki', 'files',
    'github', 'figshare',
    'zotero',
]
settings.ADDON_CATEGORIES = ['documentation', 'storage', 'bibliography']

_LOG_TEMPLATES = 'website/templates/_log_templates.mako'
LOG_TEMPLATES = 'website/templates/log_templates.mako'

try:
    shutil.copyfile(_LOG_TEMPLATES, LOG_TEMPLATES)
except OSError:
    pass

ADDONS_AVAILABLE = []
for addon_name in settings.ADDONS_REQUESTED:
    addon = init_addon(app, addon_name)
    if addon:
        ADDONS_AVAILABLE.append(addon)
settings.ADDONS_AVAILABLE = ADDONS_AVAILABLE

settings.ADDONS_AVAILABLE_DICT = {
    addon.short_name: addon
    for addon in settings.ADDONS_AVAILABLE
}

init_app('website.settings', set_backends=True, routes=True)

ensure_schemas()

if __name__ == '__main__':
    app.run(port=5000)
