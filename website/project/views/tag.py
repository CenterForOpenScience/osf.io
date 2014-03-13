import httplib as http

from website.util.sanitize import clean_tag
from website.project.model import Tag
from website.project.decorators import (
    must_be_valid_project, must_have_permission, must_not_be_registration
)


def project_tag(tag):
    backs = Tag.load(tag).node__tagged
    if backs:
        nodes = [obj for obj in backs if obj.is_public]
    else:
        nodes = []
    return {
        'nodes' : [
            {
                'title': node.title,
                'url': node.url,
            }
            for node in nodes
        ]
    }


@must_be_valid_project # returns project
@must_have_permission('write')
@must_not_be_registration
def project_addtag(**kwargs):

    tag = clean_tag(kwargs['tag'])
    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']

    if(tag):
        node_to_use.add_tag(tag=tag, auth=auth)
        return {'status': 'success'}, http.CREATED


@must_be_valid_project # returns project
@must_have_permission('write')
@must_not_be_registration
def project_removetag(**kwargs):

    tag = clean_tag(kwargs['tag'])
    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']

    if tag:
        node_to_use.remove_tag(tag=tag, auth=auth)
        return {'status': 'success'}
