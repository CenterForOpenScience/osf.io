# -*- coding: utf-8 -*-

import httplib as http

from flask import request

from website.project.decorators import (
    must_be_valid_project, must_have_permission
)
from website.util.permissions import ADMIN

from ..model import ApiKey
from .node import _view_project


@must_be_valid_project
@must_have_permission(ADMIN)
def get_node_keys(node, **kwargs):
    return {
        'keys': [
            {
                'key': key._id,
                'label': key.label,
            }
            for key in node.api_keys
        ]
    }

@must_be_valid_project
@must_have_permission(ADMIN)
def create_node_key(node, **kwargs):

    # Generate key
    api_key = ApiKey(label=request.form['label'])
    api_key.save()

    # Append to node
    node.api_keys.append(api_key)
    node.save()

    # Return response
    return {'response': 'success'}, http.CREATED

@must_be_valid_project
@must_have_permission(ADMIN)
def revoke_node_key(node, **kwargs):

    # Load key
    api_key = ApiKey.load(request.form['key'])

    # Remove from user
    node.api_keys.remove(api_key)
    node.save()

    # Send response
    return {'response': 'success'}

@must_be_valid_project
@must_have_permission(ADMIN)
def node_key_history(auth, node, **kwargs):

    api_key = ApiKey.load(kwargs['kid'])

    rv = {
        'key': api_key._id,
        'label': api_key.label,
        'route': '/settings',
        'logs': [
            {
                'lid': log._id,
                'nid': log.node__logged[0]._id,
                'route': log.node__logged[0].url,
            }
            for log in api_key.nodelog__created
        ]
    }

    rv.update(_view_project(node, auth))
    return rv
