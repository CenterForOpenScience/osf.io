# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/defaults.py

NOTE: local.py will not be added to source control.
'''

#WATERBUTLER_URL = 'http://localhost:7777'
#WATERBUTLER_INTERNAL_URL = WATERBUTLER_URL

USE_EXTERNAL_EMBER = True
PROXY_EMBER_APPS = False
EXTERNAL_EMBER_APPS = {
    'ember_osf_web': {
        'url': '/ember_osf_web/',
        'server': 'http://localhost:4200',
        'path': '/ember_osf_web/'
    },
    'preprints': {
        'url': '/preprints/',
        'server': 'http://192.168.168.167:4201/',
        'path': '/preprints/'
    },
    'registries': {
        'url': '/registries/',
        'server': 'http://192.168.168.167:4202',
        'path': '/registries/'
    },
    'reviews': {
        'url': '/reviews/',
        'server': 'http://localhost:4203',
        'path': '/reviews/'
    }
    # 'meetings': {
    #     'url': '/meetings/',
    #     'server': 'http://localhost:4201',
    #     'path': '../osf-meetings/dist/'
    # },
}

USE_CDN_FOR_CLIENT_LIBS = False

# Example of extending default settings
# defaults.IMG_FMTS += ["pdf"]
