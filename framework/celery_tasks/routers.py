# -*- coding: utf-8 -*-
from website.settings import CeleryConfig

def match_by_module(task_path):
    task_parts = task_path.split('.')
    for i in range(2, len(task_parts) + 1):
        task_subpath = '.'.join(task_parts[:i])
        if task_subpath in CeleryConfig.low_pri_modules:
            return CeleryConfig.task_low_queue
        if task_subpath in CeleryConfig.med_pri_modules:
            return CeleryConfig.task_med_queue
        if task_subpath in CeleryConfig.high_pri_modules:
            return CeleryConfig.task_low_queue
    return CeleryConfig.task_default_queue


class CeleryRouter(object):
    def route_for_task(self, task, args=None, kwargs=None):
        """ Handles routing of celery tasks.
        See http://docs.celeryproject.org/en/latest/userguide/routing.html#routers

        :param str task:    Of the form 'full.module.path.to.class.function'
        :returns dict:      Tells celery into which queue to route this task.
        """
        return {
            'queue': match_by_module(task)
        }
