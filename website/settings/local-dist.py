# -*- coding: utf-8 -*-
'''Example settings/local.py file.
These settings override what's in website/settings/base.py
'''

from . import base

dev_mode = True
mongo_uri = 'mongodb://localhost:20771/osf20130903'

# Comment out to use solr in development
use_solr = False
