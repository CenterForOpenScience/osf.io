import httplib as http

from website.addons.dataverse.client import connect_from_settings_or_403, \
    get_dataverse, get_study
from website.addons.dataverse.settings import HOST
from website.project.decorators import must_be_contributor_or_public, \
    must_have_addon


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_widget(node_addon, **kwargs):

    node = node_addon.owner
    widget_url = node.api_url_for('dataverse_get_widget_contents')

    rv = {
        'complete': node_addon.is_fully_configured,
        'widget_url': widget_url,
    }
    rv.update(node_addon.config.to_json())

    return rv, http.OK


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_get_widget_contents(node_addon, **kwargs):

    data = {
        'connected': False,
    }

    if not node_addon.is_fully_configured:
        return {'data': data}, http.OK

    doi = node_addon.study_hdl
    alias = node_addon.dataverse_alias

    connection = connect_from_settings_or_403(node_addon.user_settings)
    dataverse = get_dataverse(connection, alias)
    study = get_study(dataverse, doi)

    if study is None:
        return {'data': data}, http.BAD_REQUEST

    dataverse_url = 'http://{0}/dvn/dv/'.format(HOST) + alias
    study_url = 'http://dx.doi.org/' + doi

    data.update({
        'connected': True,
        'dataverse': node_addon.dataverse,
        'dataverseUrl': dataverse_url,
        'study': node_addon.study,
        'doi': doi,
        'studyUrl': study_url,
        'citation': study.citation,
    })
    return {'data': data}, http.OK


