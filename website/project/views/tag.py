
from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor
from framework.auth import must_have_session_auth
from ..model import Tag


def project_tag(tag):
    backs = Tag.load(tag).node__tagged
    if backs:
        nodes = [obj for obj in backs if obj.is_public]
    else:
        nodes = []
    return {
        'nodes' : [
            {
                'title' : node.title,
                'url' : node.url(),
            }
            for node in nodes
        ]
    }


@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addtag(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    tag = kwargs['tag']

    node_to_use.add_tag(tag=tag, user=user)

    return {'status' : 'success'}


@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_removetag(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    tag = kwargs['tag']

    node_to_use.remove_tag(tag=tag, user=user)

    return {'status' : 'success'}
