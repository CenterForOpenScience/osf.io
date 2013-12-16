"""
Add missing backrefs where needed.
"""

import time

from website.app import init_app
from website import models

from modularodm.storedobject import ensure_backrefs

import logging
logging.basicConfig(level=logging.DEBUG)

app = init_app()

def clean_backrefs_files():
    for record in models.NodeFile.find():
        ensure_backrefs(record, ['node', 'uploader'])

def clean_backrefs_logs():
    for record in models.NodeLog.find():
        ensure_backrefs(record, ['user', 'api_key'])

if __name__ == '__main__':
    t0 = time.time()
    clean_backrefs_files()
    clean_backrefs_logs()
    logging.debug('Spent {}'.format(time.time() - t0))