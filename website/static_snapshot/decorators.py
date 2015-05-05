# -*- coding: utf-8 -*-
import os
import functools

from flask import request
from werkzeug.contrib.cache import SimpleCache
from website.static_snapshot import tasks
from website.static_snapshot.utils import get_path
from website.models import Node


cache = SimpleCache()


def gets_static_snapshot(page_name):
    """
    Performs a background celery task that calls phantom server to
    get the static snapshot of current page.

    :param page_name: Name of the page
    :return: Decorator function
    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            # Do not allow phantom or API calls to run this task
            if not ('Phantom' in request.user_agent.string
                    or 'api/v1' in request.url):
                if cache.get(page_name) == 'pending':
                    print "Pending"  # TODO(kush): Handle this gracefully

                else:
                    print request.url
                    print page_name
                    id = ''
                    category = ''
                    # Only public projects
                    if kwargs.get('pid') or kwargs.get('nid'):
                        # kwargs['project'], kwargs['node'] = _kwargs_to_nodes(kwargs)
                        node = Node.load(kwargs.get('pid', kwargs.get('nid')))
                        if node.is_public:
                            id = kwargs.get('pid') or kwargs.get('nid')
                            category = 'node'
                        else:
                            print "Private Project"
                            return func(*args, **kwargs)

                    if kwargs.get('uid'):
                        id = kwargs.get('uid')
                        category = 'user'

                    path = get_path(page_name, id, category)
                    print path['full_path']
                    if not os.path.exists(path['full_path']):
                        task = tasks.get_static_snapshot.apply_async(args=[request.url, path['path']])
                        # Retrieve these cache values in snapshot handler
                        cache.set(page_name, 'pending')
                        cache.set('task_id', task.id)
                        cache.set('current_page', page_name)
                    else:
                        print "Already Cached"
                        with open(path['full_path'], 'r') as fp:
                            file_content = fp.read().decode('utf-8')
                            cache.set('cached_content', file_content)

            return func(*args, **kwargs)

        return wrapped

    return wrapper

