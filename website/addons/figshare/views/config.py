import httplib as http
from re import search

from framework import request
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon

from ..api import Figshare

@must_be_contributor
@must_have_addon('figshare', 'node')
def figshare_set_config(*args, **kwargs):

    user = kwargs['auth'].user
   
    figshare_user = user.get_addon('figshare')
    figshare_node = kwargs['node_addon']

    # If authorized, only owner can change settings
    if figshare_user and figshare_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)
    
    figshare_id = figshare_node.figshare_id
    figshare_type = figshare_node.figshare_type

    figshare_url = request.json.get('figshare_id', '')
    if search('projects', figshare_url):
        figshare_type = 'project'
        figshare_id = figshare_url.split('/')[-1]
    else:
        figshare_type = 'article'
        figshare_id = figshare_url.split('/')[-1]

    if not figshare_id:
        raise HTTPError(http.BAD_REQUEST)
    
    changed = (
        figshare_id != figshare_node.figshare_id or 
        figshare_type != figshare.node.figshare_type
    )
    
    if changed:
        figshare_node.figshare_id = figshare_id
        figshare_node.figshare_type = figshare_type
        figshare_node.save()
        

