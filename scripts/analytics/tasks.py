import matplotlib

from framework.celery_tasks import app as celery_app
from scripts import utils as scripts_utils

from website.app import init_app
from .logger import logger


@celery_app.task(name='scripts.analytics.tasks')
def analytics():
    matplotlib.use('Agg')
    init_app(routes=False)
    scripts_utils.add_file_logger(logger, __file__)
    from scripts.analytics import (
        logs, addons, comments, folders, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    modules = (
        logs, addons, comments, folders, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    for module in modules:
        module.main()
