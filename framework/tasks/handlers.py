# -*- coding: utf-8 -*-

from flask import g
from celery import group


def celery_before_request():
    g._celery_tasks = []


def celery_teardown_request(error=None):
    if error is None and g._celery_tasks:
        group(*g._celery_tasks)()


def enqueue_task(signature):
    if signature not in g._celery_tasks:
        g._celery_tasks.append(signature)


handlers = {
    'before_request': celery_before_request,
    'teardown_request': celery_teardown_request,
}
