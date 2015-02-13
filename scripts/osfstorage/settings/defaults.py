#!/usr/bin/env python
# encoding: utf-8

import hashlib

from cloudstorm.backend import contrib


STORAGE_CLIENT_CLASS = contrib.cloudfiles.CloudFilesClient
STORAGE_CLIENT_OPTIONS = {
    'username': None,
    'api_key': None,
    'region': None,
}
STORAGE_CONTAINER_NAME = None

UPLOAD_PRIMARY_HASH = hashlib.sha256

SPECIAL_CASES = {}

USERNAME = 'changeme'
API_KEY = 'changeme'
REGION = 'changeme'

AWS_ACCESS_KEY = 'changeme'
AWS_SECRET_KEY = 'changeme'
AUDIT_TEMP_PATH = 'audit'
