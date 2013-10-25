#!/usr/bin/env python
# -*- coding: utf-8 -*-
from website.app import init_app


from website.project.model import ensure_schemas

if __name__ == '__main__':
    app = init_app("website.settings", set_backends=True, routes=True)
    ensure_schemas()
    app.run(port=5000)
