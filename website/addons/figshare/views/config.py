import httplib as http
from re import search, split

from framework import request
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon


@must_be_contributor
@must_have_addon('figshare', 'node')
def figshare_set_config(*args, **kwargs):

    auth = kwargs['auth']
    user = auth.user

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    user_settings = node_settings.user_settings

    # If authorized, only owner can change settings
    if user_settings and user_settings.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    figshare_id = node_settings.figshare_id
    figshare_type = node_settings.figshare_type

    figshare_url = request.json.get('figshare_id', '')

    if search('project', figshare_url):
        figshare_type = 'project'
        figshare_id = split(r'[\_/]', figshare_url)[-1]
    else:
        figshare_type = 'article'
        figshare_id = split(r'[\_/]', figshare_url)[-1]

    if not figshare_id:
        raise HTTPError(http.BAD_REQUEST)

    changed = (
        figshare_id != node_settings.figshare_id or
        figshare_type != node_settings.figshare_type
    )

    if changed:
        node_settings.figshare_id = figshare_id
        node_settings.figshare_type = figshare_type
        #Add project name here
        node_settings.save()

        node.add_log(
            action='figshare_content_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'figshare': {
                    'type': figshare_type,
                    'id': figshare_id
                }
            },
            auth=auth,
        )

    return {}


@must_be_contributor
@must_have_addon('figshare', 'node')
def figshare_unlink(*args, **kwargs):
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    figshare_user = auth.user.get_addon('figshare')
    figshare_node = kwargs['node_addon']

    # If authorized, only owner can change settings
    if figshare_user and figshare_user.owner != auth.user:
        raise HTTPError(http.BAD_REQUEST)
    node.add_log(
        action='figshare_content_unlinked',
        params={
            'project': node.parent_id,
            'node': node._id,
            'figshare': {
                'type': figshare_node.figshare_type,
                'id': figshare_node.figshare_id
            }
        },
        auth=auth,
    )

    figshare_node.figshare_id = None
    figshare_node.figshare_type = None
    figshare_node.save()
