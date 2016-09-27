import httplib as http

from flask import request
from modularodm import Q
from modularodm.exceptions import ValidationError

from framework.auth.decorators import collect_auth
from website.exceptions import InvalidTagError, NodeStateError, TagNotFoundError
from website.project.model import Node, Tag
from website.project.decorators import (
    must_be_valid_project, must_have_permission, must_not_be_registration
)


# Disabled for now. Should implement pagination, or at least cap the number of
# nodes serialized, before re-enabling.
@collect_auth
def project_tag(tag, auth, **kwargs):
    tag_obj = Tag.load(tag)
    if tag_obj:
        nodes = Node.find(Q('tags', 'eq', tag_obj._id))
    else:
        nodes = []

    visible_nodes = [obj for obj in nodes if obj.can_view(auth)]
    return {
        'nodes': [
            {
                'title': node.title,
                'url': node.url,
            }
            for node in visible_nodes
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
