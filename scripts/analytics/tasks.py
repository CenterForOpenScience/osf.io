import matplotlib

from framework.celery_tasks import app as celery_app

from website.app import init_app


@celery_app.task(name='scripts.analytics.tasks')
def analytics():
    matplotlib.use('Agg')
    init_app(routes=False)
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
