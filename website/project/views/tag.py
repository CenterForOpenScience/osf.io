import http.client as http

from flask import request
from django.core.exceptions import ValidationError

from framework.auth.decorators import collect_auth
from osf.models import AbstractNode
from osf.exceptions import InvalidTagError, NodeStateError, TagNotFoundError
from website.project.decorators import (
    must_be_valid_project, must_have_permission, must_not_be_registration
)


# Disabled for now. Should implement pagination, or at least cap the number of
# nodes serialized, before re-enabling.
@collect_auth
def project_tag(tag, auth, **kwargs):
    nodes = AbstractNode.objects.filter(tags___id=tag).can_view(auth.user).values('title', 'url')
    return {
        'nodes': [
            {
                'title': node['title'],
                'url': node['url'],
            }
            for node in nodes
        ],
        'tag': tag,
    }


@must_be_valid_project  # injects project
@must_have_permission('write')
@must_not_be_registration
def project_add_tag(auth, node, **kwargs):

    data = request.get_json()
    tag = data['tag']
    if tag:
        try:
            node.add_tag(tag=tag, auth=auth)
            return {'status': 'success'}, http.CREATED
        except ValidationError:
            return {'status': 'error'}, http.BAD_REQUEST


@must_be_valid_project  # injects project
@must_have_permission('write')
@must_not_be_registration
def project_remove_tag(auth, node, **kwargs):
    data = request.get_json()
    try:
        node.remove_tag(tag=data['tag'], auth=auth)
    except TagNotFoundError:
        return {'status': 'failure'}, http.CONFLICT
    except (InvalidTagError, NodeStateError):
        return {'status': 'failure'}, http.BAD_REQUEST
    else:
        return {'status': 'success'}, http.OK
