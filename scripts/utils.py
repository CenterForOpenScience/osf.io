# -*- coding: utf-8 -*-

import os
import logging
import datetime
import shutil

from werkzeug.local import LocalProxy

from framework.mongo import database
from framework.transactions.context import transaction

from website import models
from website import settings


def format_now():
    return datetime.datetime.now().isoformat()


def add_file_logger(logger, script_name, suffix=None):
    _, name = os.path.split(script_name)
    if suffix is not None:
        name = '{0}-{1}'.format(name, suffix)
    file_handler = logging.FileHandler(
        os.path.join(
            settings.LOG_PATH,
            '.'.join([name, format_now(), 'log'])
        )
    )
    logger.addHandler(file_handler)


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