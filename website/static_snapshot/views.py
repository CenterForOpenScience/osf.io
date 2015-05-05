import os

from flask import request
from flask import render_template
from framework.render.tasks import ensure_path
from framework.flask import redirect
from website.static_snapshot import tasks
from website.models import Node
from website.util import web_url_for


def get_static_snapshot(cache):
    """
    View function to handle the url call made by google bot crawler
    """
    response = {}
    task_id = cache.get('task_id')
    task = tasks.get_static_snapshot.AsyncResult(task_id)
    # page_name = cache.get('page_name')
    print task
    # import pdb; pdb.set_trace()
    print request.url
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


def get_url(node, page):
    """
    Helper function that distinguishes googlebot requests from the regular requests
    """
    urls = {
        'files': node.web_url_for('collect_file_trees'),
        'wiki': node.web_url_for('project_wiki_home'),
        'statistics': node.web_url_for('project_statistics'),
        'forks': node.web_url_for('node_forks'),
        'registrations': node.web_url_for('node_registrations'),
    }

    return urls[page]