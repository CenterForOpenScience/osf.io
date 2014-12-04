#!/usr/bin/env python
# -*- coding: utf-8 -*-

from website.app import init_app

app = init_app('website.settings', set_backends=True, routes=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
