#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from website import settings
from website.app import init_app

app = init_app('website.settings', set_backends=True, routes=True)

if __name__ == '__main__':
    host = os.environ.get('OSF_HOST', None)
    port = os.environ.get('OSF_PORT', None)
    if port:
        port = int(port)

    app.run(host=host, port=port, extra_files=[settings.ASSET_HASH_PATH])
