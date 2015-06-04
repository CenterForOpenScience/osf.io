# -*- coding: utf-8 -*-

import unittest

import os
import shutil

from werkzeug.local import LocalProxy

from framework.mongo import database
from framework.transactions.context import transaction

from website import models
from website import settings


def _get_backup_collection():
    return database[settings.NODE_BACKUP_COLLECTION]
backup_collection = LocalProxy(_get_backup_collection)


def backup_node_git(node):
    source_path = os.path.join(settings.UPLOADS_PATH, node._id)
    if not os.path.exists(source_path):
        return
    dest_path = os.path.join(settings.UPLOADS_BACKUP_PATH, node._id)
    shutil.move(source_path, dest_path)


@transaction()
def backup_node_mongo(node):
    data = node.to_storage()
    backup_collection.insert(data)
    models.Node.remove_one(node)


class UploadsBackupTestCase(unittest.TestCase):

    UPLOADS_BACKUP_PATH = getattr(
        settings,
        'TEST_UPLOADS_BACKUP_PATH',
        '/tmp/test_uploads_backup',
    )

    @classmethod
    def setUpClass(cls):
        super(UploadsBackupTestCase, cls).setUpClass()
        try:
            os.mkdir(cls.UPLOADS_BACKUP_PATH)
        except OSError:
            pass
        cls._UPLOADS_BACKUP_PATH, settings.UPLOADS_BACKUP_PATH = (
            settings.UPLOADS_BACKUP_PATH, cls.UPLOADS_BACKUP_PATH
        )

    @classmethod
    def tearDownClass(cls):
        super(UploadsBackupTestCase, cls).tearDownClass()
        shutil.rmtree(cls.UPLOADS_BACKUP_PATH)
        settings.UPLOADS_BACKUP_PATH = cls._UPLOADS_BACKUP_PATH

