#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil

from framework import app

from website import settings
from website.app import init_app
from website.project.model import ensure_schemas

try:
    shutil.copyfile(
        settings.BASE_LOG_TEMPLATES,
        settings.GENERATED_LOG_TEMPLATES
    )
except OSError:
    pass

init_app('website.settings', set_backends=True, routes=True)

ensure_schemas()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
