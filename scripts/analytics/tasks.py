import matplotlib

from framework.tasks import app as celery_app

from website.app import init_app

from scripts.analytics import (
    logs, addons, comments, folders, links, watch, email_invites,
    permissions, profile, benchmarks
)


@celery_app.task(name='scripts.analytics.tasks')
def analytics():
    matplotlib.use('Agg')
    init_app()
    modules = (
        logs, addons, comments, folders, links, watch, email_invites,
        permissions, profile, benchmarks
    )
    for module in modules:
        module.main()