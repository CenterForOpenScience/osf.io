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
from osf.models import Guid


logger = logging.getLogger(__name__)

@must_be_contributor_or_public
def get_init_timestamp_error_data_list(auth, node, **kwargs):
    """
     get timestamp error data list (OSF view)
    """

    ctx = _view_project(node, auth, primary=True)
    ctx.update(rubeus.collect_addon_assets(node))
    pid = kwargs.get('pid')
    ctx['provider_list'] = timestamp.get_error_list(pid)
    ctx['project_title'] = node.title
    ctx['guid'] = pid
    ctx['web_api_url'] = settings.DOMAIN + node.api_url
    return ctx

@must_be_contributor_or_public
def get_timestamp_error_data(auth, node, **kwargs):
    # timestamp error data to timestamp or admin view
    if request.method == 'POST':
        request_data = request.json
        data = {}
        for key in request_data.keys():
            data.update({key: request_data[key][0]})
    else:
        data = request.args.to_dict()

    return timestamp.check_file_timestamp(auth.user.id, node, data)

@must_be_contributor_or_public
def add_timestamp_token(auth, node, **kwargs):
    '''
    Timestamptoken add method
    '''
    if request.method == 'POST':
        request_data = request.json
        data = {}
        for key in request_data.keys():
            data.update({key: request_data[key][0]})
    else:
        data = request.args.to_dict()

    return timestamp.add_token(auth.user.id, node, data)

@must_be_contributor_or_public
def collect_timestamp_trees_to_json(auth, node, **kwargs):
    # admin call project to provider file list
    serialized = _view_project(node, auth, primary=True)
    serialized.update(rubeus.collect_addon_assets(node))
    uid = Guid.objects.get(_id=serialized['user']['id']).object_id
    pid = kwargs.get('pid')
    return {'provider_list': timestamp.get_full_list(uid, pid, node)}
