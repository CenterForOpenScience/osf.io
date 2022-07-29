"""
Files views.
"""
import waffle
from flask import request

from osf import features
from osf.models import Node, Registration

from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public, must_not_be_retracted_registration
from website.project.views.node import _view_project
from website.ember_osf_web.views import use_ember_app


@must_not_be_retracted_registration
@must_be_contributor_or_public
def collect_file_trees(auth, node, **kwargs):
    """Collect file trees for all add-ons implementing HGrid views, then
    format data as appropriate.
    """
    if isinstance(node, Node) and waffle.flag_is_active(request, features.EMBER_PROJECT_FILES):
        return use_ember_app()

    if isinstance(node, Registration) and waffle.flag_is_active(request, features.EMBER_REGISTRATION_FILES):
        return use_ember_app()

    serialized = _view_project(node, auth, primary=True)
    # Add addon static assets
    serialized.update(rubeus.collect_addon_assets(node))
    return serialized

@must_be_contributor_or_public
def grid_data(auth, node, **kwargs):
    """View that returns the formatted data for rubeus.js/hgrid
    """
    data = request.args.to_dict()
    return {'data': rubeus.to_hgrid(node, auth, **data)}
