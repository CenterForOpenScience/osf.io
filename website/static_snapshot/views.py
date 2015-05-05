import os

from framework.render.tasks import ensure_path
from website.static_snapshot import tasks


def get_static_snapshot(cache):
    """
    View function to handle the url call made by google bot crawler
    """
    response = {}
    task_id = cache.get('task_id')
    task = tasks.get_static_snapshot.AsyncResult(task_id)
    if task.id:

        if task.state == 'PENDING':
            print "Waiting for a response from celery task"

        elif task.state == 'SUCCESS':
            print "Save to cache"
            path = task.result['path']
            ensure_path(path)
            current_page = cache.get('current_page')
            file_name = os.path.join(path, current_page) + '.html'
            file_content = task.result['content'].encode('utf-8')
            with open(file_name, 'wb') as fp:
                fp.write(file_content)
            cache.clear()
            response = {'content': task.result['content']}
        else:
            print " Invalid Celery task"
    elif cache.get('cached_content'):
        print "Already cached/ Not valid request"
        response = {'content': cache.get('cached_content')}
        cache.clear()
    else:
        print "No task Id"

    return response
