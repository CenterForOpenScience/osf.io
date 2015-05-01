import os

from celery.backends import cache
from framework.render.tasks import ensure_path
from website.static_snapshot import tasks
from website.static_snapshot.decorators import cache


def handle_get_static_snapshot(**kwargs):
    print "in handler"
    task_id = cache.get('task_id')
    task = tasks.get_static_snapshot.AsyncResult(task_id)
    page_name = cache.get('page_name')
    print task
    response = {}

    if task.state == 'FAIL':
        print " Cache already exists"
        

    if task.state == 'PENDING':
        print "Waiting for a response from celery task"
        cache.set(page_name, 'pending')

    if task.state == 'SUCCESS':
        print "Save to cache"
        path = task.result['path']
        ensure_path(path)
        file = os.path.join(path, task_id + '.html')
        file_content = task.result['content'].encode('utf-8')
        with open(file, 'wb') as fp:
            fp.write(file_content)
        response = {
            'state': task.state,
            'content': task.info['content']
        }
    return response