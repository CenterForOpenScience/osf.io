# -*- coding: utf-8 -*-
from website.settings import DEFAULT_QUEUE, LOW_QUEUE, MED_QUEUE, HIGH_QUEUE

LOW_PRI_MODULES = {
    'framework.analytics.tasks',
    'framework.celery_tasks',
    'scripts.osfstorage.usage_audit',
    'scripts.osfstorage.glacier_inventory',
    'scripts.analytics.tasks',
    'scripts.osfstorage.files_audit',
    'scripts.osfstorage.glacier_audit',
    'scripts.populate_new_and_noteworthy_projects',
    'website.search.elastic_search',
}

MED_PRI_MODULES = {
    'framework.email.tasks',
    'scripts.send_queued_mails',
    'scripts.triggered_mails',
    'website.mailchimp_utils',
    'website.notifications.tasks',
}

HIGH_PRI_MODULES = {
    'scripts.approve_embargo_terminations',
    'scripts.approve_registrations',
    'scripts.embargo_registrations',
    'scripts.refresh_box_tokens',
    'scripts.retract_registrations',
    'website.archiver.tasks',
}

def match_by_module(task_path):
    task_parts = task_path.split('.')
    for i in range(2, len(task_parts) + 1):
        task_subpath = '.'.join(task_parts[:i])
        if task_subpath in LOW_PRI_MODULES:
            return LOW_QUEUE
        if task_subpath in MED_PRI_MODULES:
            return MED_QUEUE
        if task_subpath in HIGH_PRI_MODULES:
            return HIGH_QUEUE
    return DEFAULT_QUEUE


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
