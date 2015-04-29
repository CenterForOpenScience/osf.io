# -*- coding: utf-8 -*-

import time
import httplib
import functools

from flask import request

from framework.sessions import session
from framework.auth import signing
from framework.flask import redirect
from framework.exceptions import HTTPError
from website.util import web_url_for
from . import tasks
from .import SNAPSHOT_PAGE


def gets_dashoard_static_snapshot(func):
    """Calls the celery task to get html static snapshot of the page
    when the page is loaded for the first time.
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        page = request.path.strip('/')
        # SNAPSHOT_PAGE['dashboard'] = True
        url = web_url_for('dashboard', _absolute=True)
        if SNAPSHOT_PAGE.get(page):  # TODO: Make use of cache
            # Celery task should run only once
            task = tasks.get_static_snapshot.apply_async(args=[url, request.cookies])
            print " celery"
            session.data[page] = {'task_id': task.id}
            SNAPSHOT_PAGE[page] = False
        return func(*args, **kwargs)
    return wrapped

def gets_project_static_snapshot(func):
    """Calls the celery task to get html static snapshot of the page
    when the page is loaded for the first time.
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        if request.path.strip('/') == kwargs['pid']:
            page = 'project'
        else:
            page = request.path.strip('/')
        print page
        url = web_url_for('view_project', _absolute=True, pid=kwargs['pid'])
        SNAPSHOT_PAGE['project'] = True
        if SNAPSHOT_PAGE.get(page):  # TODO: Make use of cache
            # Celery task should run only once
            task = tasks.get_static_snapshot.apply_async(args=[url, request.cookies])
            print " celery"
            print url
            session.data[page] = {'task_id': task.id}
            SNAPSHOT_PAGE[page] = False
        return func(*args, **kwargs)
    return wrapped