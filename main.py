#!/usr/bin/env python
# -*- coding: utf-8 -*-
from website.app import init_app


if __name__ == '__main__':
    app = init_app("website.settings", set_backends=True, routes=True)
    app.run(port=5000)
