"""
Files views.
"""
from flask import request

from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public, must_not_be_retracted_registration
from website.project.views.node import _view_project
from website.ember_osf_web.decorators import ember_flag_is_active
from addons.osfstorage.models import NodeSettings

@must_not_be_retracted_registration
@must_be_contributor_or_public
@ember_flag_is_active('ember_project_files_page')
def collect_file_trees(auth, node, **kwargs):
    """Collect file trees for all add-ons implementing HGrid views, then
    format data as appropriate.
    """
    serialized = _view_project(node, auth, primary=True)
    # Add addon static assets
    serialized.update(rubeus.collect_addon_assets(node))
    return serialized

@must_be_contributor_or_public
def grid_data(auth, node, **kwargs):
    """View that returns the formatted data for rubeus.js/hgrid
    """
    data = request.args.to_dict()
    ret = rubeus.to_hgrid(node, auth, **data)
    import logging
    logging.critical("#######################################")
    for x in NodeSettings.objects.filter(owner_id=node.id):
        logging.critical(vars(x))
    logging.critical("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    try:
        if NodeSettings.objects.get(owner_id=node.id).region_id != 1:
            ret[0]['children'][0]['iconUrl'] = '/static/addons/osfstorage/comicon_custom_storage.png'
            ret[0]['children'][0]['addonFullname'] = ret[0]['children'][0]['nodeRegion']
    except Exception as error: 
        logging.critical(error)
    return {'data': ret}
