# -*- coding: utf-8 -*-

class CeleryRouter(object):
    def route_for_task(self, task, args=None, kwargs=None):
        """ Handles routing of celery tasks.
        See http://docs.celeryproject.org/en/latest/userguide/routing.html#routers

        :param str task:    Of the form 'full.module.path.to.class.function'
        :returns dict:      Tells celery how to route this task.
        """
        if 'website.mailing_list' in task:
            return {
                'queue': 'mailing_list',
            }
        return {
            'queue': 'celery'  # Default queue
        }
