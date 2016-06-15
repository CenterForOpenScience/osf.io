"""
Files views.
"""
from flask import request

from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project


@must_be_contributor_or_public
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

    data = {'data': rubeus.to_hgrid(node, auth, **data)}
    return data
