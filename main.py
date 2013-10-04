#!/usr/bin/env python
# -*- coding: utf-8 -*-
import framework

import website.settings
import website.models
import website.routes

# from website.addons.dataverse import route

app = framework.app

static_folder = website.settings.static_path

import new_style

if __name__ == '__main__':

    app.run(port=5000, debug=True)
