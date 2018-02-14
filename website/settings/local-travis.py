# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''
import logging

import os


USE_EXTERNAL_EMBER = True
EXTERNAL_EMBER_APPS = {
    'ember_osf_web': {
        'url': '/ember_osf_web/',
        'server': 'http://localhost:4200',
        'path': os.environ.get('HOME') + '/ember_osf_web/'
    },
    'preprints': {
        'url': '/preprints/',
        'server': 'http://localhost:4201',
        'path': os.environ.get('HOME') + '/preprints/'
    }
}

USE_CDN_FOR_CLIENT_LIBS = False

NEW_AND_NOTEWORTHY_LINKS_NODE = 'helloo'
POPULAR_LINKS_NODE = 'hiyah'
POPULAR_LINKS_REGISTRATIONS = 'woooo'

logging.getLogger('celery.app.trace').setLevel(logging.FATAL)
