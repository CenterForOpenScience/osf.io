import httplib as http

from flask import request
from modularodm.exceptions import ValidationError

from framework.auth.decorators import collect_auth
from framework.guid.model import Guid
from website.project.model import Tag
from website.project.decorators import (
    must_be_valid_project, must_have_permission, must_not_be_registration
)


# Disabled for now. Should implement pagination, or at least cap the number of
# nodes serialized, before re-enabling.
@collect_auth
def project_tag(tag, auth, **kwargs):
    tag_obj = Tag.load(tag)
    nodes = tag_obj.node__tagged if tag_obj else []
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
    tag = data['tag']
    if tag:
        node.remove_tag(tag=tag, auth=auth)
        return {'status': 'success'}


@must_be_valid_project  # injects project
@must_have_permission('write')
@must_not_be_registration
def file_add_tag(auth, node, guid, **kwargs):
    data = request.get_json()
    tag = data['tag']
    file_name = data['fileName']
    if tag:
        try:
            fileobject = Guid.load(guid).referent
            fileobject.add_tag(tag, auth, node, file_name)
            return {'status': 'success'}, http.CREATED
        except ValidationError:
            return {'status': 'error'}, http.BAD_REQUEST


@must_be_valid_project  # injects project
@must_have_permission('write')
@must_not_be_registration
def file_remove_tag(auth, node, guid, **kwargs):
    data = request.get_json()
    tag = data['tag']
    file_name = data['fileName']
    if tag:
        fileobject = Guid.load(guid).referent
        fileobject.remove_tag(tag, auth, node, file_name)
        return {'status': 'success'}
