#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil

from framework import app

from website.app import init_app
from website.project.model import ensure_schemas

_LOG_TEMPLATES = 'website/templates/_log_templates.mako'
LOG_TEMPLATES = 'website/templates/log_templates.mako'

try:
    shutil.copyfile(_LOG_TEMPLATES, LOG_TEMPLATES)
except OSError:
    pass

init_app('website.settings', set_backends=True, routes=True)

ensure_schemas()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
