#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all()

# PATCH: avoid deadlock on getaddrinfo, this patch is necessary while waiting for
# the final gevent 1.1 release (https://github.com/gevent/gevent/issues/349)
unicode('foo').encode('idna')  # noqa


import os  # noqa

from website import settings  # noqa
from website.app import init_app  # noqa

application = app = init_app('website.settings', set_backends=True, routes=True)

if __name__ == '__main__':
    host = os.environ.get('OSF_HOST', None)
    port = os.environ.get('OSF_PORT', None)
    if port:
        port = int(port)

    app.run(host=host, port=port, extra_files=[settings.ASSET_HASH_PATH], threaded=settings.DEBUG_MODE)
