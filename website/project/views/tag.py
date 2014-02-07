from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor
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
                'url' : node.url,
            }
            for node in nodes
        ]
    }


@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addtag(*args, **kwargs):

    tag = kwargs['tag']
    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']

    node_to_use.add_tag(tag=tag, auth=auth)

    return {'status' : 'success'}, 201


@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_removetag(*args, **kwargs):

    tag = kwargs['tag']
    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']

    node_to_use.remove_tag(tag=tag, auth=auth)

    return {'status' : 'success'}
