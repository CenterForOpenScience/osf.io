import httplib

from flask import request

from website.addons.base import exceptions 
from website.addons.sharelatex import utils
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public


@must_be_contributor_or_public
@must_have_addon('sharelatex', 'node')
@must_have_permission('write')
def sharelatex_new_project(auth, node_addon, **kwargs):
    project_name = request.json.get('project_name', '')
    project_location = request.json.get('project_location', '')

    if not utils.validate_project_name(project_name):
        return {
            'message': 'That project name is not valid.',
            'title': 'Invalid project name',
        }, httplib.NOT_ACCEPTABLE

    # Get location and verify it is valid
    if not utils.validate_project_location(project_location):
        return {
            'message': 'That project location is not valid.',
            'title': 'Invalid project location',
        }, httplib.NOT_ACCEPTABLE

    try:
        utils.new_project(node_addon.user_settings, project_name, project_location)
    except exception as e:
        return {
            'message': e.message,
            'title': 'Problem connecting to ShareLatex',
        }, httplib.NOT_ACCEPTABLE
    except exception.ShareLatexCreateError as e:
        return {
            'message': e.message,
            'title': "Problem creating project '{0}'".format(project_name),
        }, httplib.NOT_ACCEPTABLE
    except exception.BotoClientError as e:  # Base class catchall
        return {
            'message': e.message,
            'title': 'Error connecting to ShareLatex',
        }, httplib.NOT_ACCEPTABLE

    return {
        'projects': utils.get_project_names(node_addon.user_settings)
    }
