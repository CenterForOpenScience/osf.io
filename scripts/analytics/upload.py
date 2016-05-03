import os

from time import sleep

from framework.celery_tasks import app as celery_app
from framework.mongo import database

from scripts.analytics import settings
from scripts.analytics import utils

from website import models
from website import settings as website_settings

from .logger import logger


@celery_app.task(name='scripts.analytics.upload')
def upload():
    for root, dirs, files in os.walk(website_settings.ANALYTICS_PATH):
        for a_dir in dirs:
            # only directories with file in it or its sub-directories will be created
            pass
        for a_file in files:
            segments = root.split('osf.io/website/analytics')
            if len(segments) != 2:
                logger.error('I/O Error: invalid root path: {}'.format(segments))
                continue
            path = segments[1]
            file_name = a_file
            waterbutler_path = '/analytics' + path
            waterbutler_upload(waterbutler_path, file_name)


def create_dir(dir_name, self_id, parent_path, parent_id):
    assert self_id is None, 'Cannot create directories that already exist'
    path = '/'
    if parent_path is not None and len(parent_path) > 0:
        path = '/' + parent_id + '/'
    name = dir_name
    create = True

    node = models.Node.load(settings.TABULATE_LOGS_NODE_ID)
    user = models.User.load(settings.TABULATE_LOGS_USER_ID)

    retry = 0
    while retry < 3:  # server 503 may still happen with sleep(1), retry for 3 times
        resp = utils.send_file(name, 'folder-upload', None, node, user, create, path)
        sleep(1)  # walk around 503 error
        if resp.status_code != 503:
            break
        retry += 1
    if retry == 3:
        resp.raise_for_status()


def create_or_update_file(file_stream, file_name, self_id, parent_path, parent_id):
    path = '/'
    if parent_path is not None:
        path = '/' + parent_id + '/'
    if self_id is None:
        name = file_name
        create = True
    else:
        name = self_id
        create = False
        path = '/'

    node = models.Node.load(settings.TABULATE_LOGS_NODE_ID)
    user = models.User.load(settings.TABULATE_LOGS_USER_ID)

    retry = 0
    while retry < 3:  # server 503 may still happen with sleep(1), retry for 3 times
        resp = utils.send_file(name, 'file-upload', file_stream, node, user, create, path)
        sleep(1)  # walk around 503 error
        if resp.status_code != 503:
            break
        retry += 1
    if retry == 3:
        logger.debug('response = {}'.format(resp.json()))
        resp.raise_for_status()


def waterbutler_upload(path, name, test_existence=False):
    assert path.startswith('/'), 'Path must always starts with /'

    root = database['storedfilenode'].find({'node': settings.ANALYTICS_LOGS_NODE_ID, 'parent': None})
    if root.count() != 1:
        logger.error('Invalid Node ID: Cannot find the project node {}.'.format(settings.ANALYTICS_LOGS_NODE_ID))
        return
    parent_id = root[0]['_id']
    parent_path = []

    for a_dir in path.split('/')[1:]:
        if a_dir == '':  # upload to the project folder
            parent_path = None
            break
        dirs = database['storedfilenode'].find({'name': a_dir, 'parent': parent_id})
        assert dirs.count() in [0, 1], 'Database query failure'
        if dirs.count() == 0:  # dir does not exsit
            if test_existence:
                return False
            else:
                create_dir(a_dir, None, parent_path, parent_id)
                dirs = database['storedfilenode'].find({'name': a_dir, 'parent': parent_id})
                if dirs.count() == 1:
                    parent_id = dirs[0]['_id']
                    parent_path.append(parent_id)
                else:
                    raise Exception('Cannot find newly created directory')
                continue
        else:  # dir found
            parent_id = dirs[0]['_id']
            parent_path.append(parent_id)
            continue

    file_path = '/' + '/'.join(website_settings.ANALYTICS_PATH.split('/')[1:-1]) + path + '/' + name
    logger.debug('file_path: {}'.format(file_path))
    with open(file_path, 'r') as file_stream:
        docs = database['storedfilenode'].find({'name': name, 'parent': parent_id})
        assert docs.count() in [0,1], 'Database query failure'
        if docs.count() == 0:
            if test_existence:
                return False
            else:
                return create_or_update_file(file_stream, name, None, parent_path, parent_id)
        elif docs.count() == 1:
            if test_existence:
                return True
            else:
                self_id = docs[0]['_id']
                return create_or_update_file(file_stream, name, self_id, parent_path, parent_id)
