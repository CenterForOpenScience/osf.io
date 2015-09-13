import json
from flask import request
from urllib2 import HTTPError
import httplib as http

from framework.auth.decorators import must_be_logged_in
from website.addons.dryad.provider import DryadProvider
from website.citations.views import GenericCitationViews
from website.project.decorators import (
    must_have_addon,
    must_have_permission,
    must_be_valid_project
)
from website.util import permissions

dryad_generic_views = GenericCitationViews('dryad', DryadProvider)

def dryad_validate_doi(**kwargs):
    """
        Checks the DOI to see if it exists in the Dryad archive.
    """
    doi = request.args['doi']
    repo = DryadProvider()
    return repo.check_dryad_doi(doi)

@must_be_logged_in
@must_have_addon('dryad', 'node')
@must_be_valid_project
@must_have_permission(permissions.WRITE)
def dryad_set_doi(node_addon, **kwargs):
    """
        Tries to set the DOI
    """
    try:
        auth = kwargs['auth']
        doi = json.loads(request.data)['doi']
        repo = DryadProvider()
        title = repo.get_dryad_title(doi)
        ret = node_addon.set_doi(doi, title, auth)
        node_addon.save()
        return ret
    except HTTPError:
        return False

@must_have_addon('dryad', 'node')
def dryad_get_current_metadata(node_addon, **kwargs):
    """
        Retrieves metadata of the currently selected package.
    """
    doi = node_addon.dryad_package_doi
    repo = DryadProvider()
    if doi is not None:
        return repo.get_dryad_metadata_as_json(doi)
    else:
        return {}

@must_have_addon('dryad', 'node')
def dryad_list_objects(node_addon, **kwargs):
    """
        Uses the Dryad object list to get a list of available packages.
    """
    repo = DryadProvider()
    count = request.args['count']
    start = request.args['start']
    return repo.get_package_list_as_json(start, count)

@must_have_addon('dryad', 'node')
def dryad_search_objects(node_addon, **kwargs):
    """
        Queries the Dryad search endpoint
    """
    repo = DryadProvider()
    count = request.args['count']
    start = request.args['start']
    query = request.args['query']
    return repo.get_dryad_search_results_json_formatted(start, count, query)

@must_have_addon('dryad', 'node')
def dryad_citation(node_addon, **kwargs):
    """
        Returns the citations for Dryad packages and publications.
    """
    doi = node_addon.dryad_package_doi
    repo = DryadProvider()
    ret = repo.get_dryad_citation(doi)
    return ret, http.OK
