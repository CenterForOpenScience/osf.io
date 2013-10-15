# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/base.py

NOTE: local.py will not be added to source control.
'''

from . import base

dev_mode = True

# Change to whatever port and db you want
MONGO_PORT = 20771
DB_NAME = "osf20130903"
mongo_uri = 'mongodb://localhost:{port}/{db}'.format(port=MONGO_PORT, db=DB_NAME)

# Comment out to use solr in development
use_solr = False
