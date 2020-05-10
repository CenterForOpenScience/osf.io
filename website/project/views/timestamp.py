# -*- coding: utf-8 -*-
"""
Timestamp views.
"""
import logging
from flask import request
from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project
from website.util import timestamp
from website import settings
from osf.models import TimestampTask

logger = logging.getLogger(__name__)

@must_be_contributor_or_public
def get_init_timestamp_error_data_list(auth, node, **kwargs):
    """get timestamp error data list (OSF view)
    """
    ctx = _view_project(node, auth, primary=True)
    ctx.update(rubeus.collect_addon_assets(node))
    pid = kwargs.get('pid')
    ctx['provider_list'] = timestamp.get_error_list(pid)
    ctx['project_title'] = node.title
    ctx['guid'] = pid
    ctx['web_api_url'] = settings.DOMAIN + node.api_url
    ctx['async_task'] = timestamp.get_async_task_data(node)
    return ctx

@must_be_contributor_or_public
def verify_timestamp_token(auth, node, **kwargs):
    async_task = timestamp.celery_verify_timestamp_token.delay(auth.user.id, node.id)
    TimestampTask.objects.update_or_create(
        node=node,
        defaults={'task_id': async_task.id, 'requester': auth.user}
    )
    return {'status': 'OK'}

@must_be_contributor_or_public
def add_timestamp_token(auth, node, **kwargs):
    """Timestamptoken add method
    """
    async_task = timestamp.celery_add_timestamp_token.delay(auth.user.id, node.id, request.json)
    TimestampTask.objects.update_or_create(
        node=node,
        defaults={'task_id': async_task.id, 'requester': auth.user}
    )
    return {'status': 'OK'}

@must_be_contributor_or_public
def download_errors(auth, node, **kwargs):
    timestamp.add_log_download_errors(node, auth.user.id)
    return {'status': 'OK'}

@must_be_contributor_or_public
def cancel_task(auth, node, **kwargs):
    return timestamp.cancel_celery_task(node)

@must_be_contributor_or_public
def task_status(auth, node, **kwargs):
    return timestamp.get_celery_task_progress(node)
