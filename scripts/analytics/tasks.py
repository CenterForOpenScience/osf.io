import os
import matplotlib

from framework.celery_tasks import app as celery_app

from scripts import utils as script_utils
from scripts.analytics import settings
from scripts.analytics import utils

from website import models
from website import settings as website_settings
from website.app import init_app

from .logger import logger


@celery_app.task(name='scripts.analytics.tasks')
def analytics():
    matplotlib.use('Agg')
    init_app(routes=False)
    script_utils.add_file_logger(logger, __file__)
    from scripts.analytics import (
        logs, addons, comments, folders, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    modules = (
        logs, addons, comments, folders, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    for module in modules:
        logger.info('Starting: {}'.format(module.__name__))
        module.main()
        logger.info('Finished: {}'.format(module.__name__))

    upload_analytics()


def upload_analytics(local_path=None, remote_path='/'):
    node = models.Node.load(settings.TABULATE_LOGS_NODE_ID)
    user = models.User.load(settings.TABULATE_LOGS_USER_ID)

    if not local_path:
        local_path = website_settings.ANALYTICS_PATH

    for name in os.listdir(local_path):
        if not os.path.isfile(os.path.join(local_path, name)):
            logger.info('create directory: {}'.format(os.path.join(local_path, name)))
            metadata = utils.create_object(name, 'folder-update', node, user, kind='folder', path=remote_path)
            upload_analytics(os.path.join(local_path, name), metadata['attributes']['path'])
        else:
            logger.info('update file: {}'.format(os.path.join(local_path, name)))
            with open(os.path.join(local_path, name), 'rb') as fp:
                utils.create_object(name, 'file-update', node, user, stream=fp, kind='file', path=remote_path)
