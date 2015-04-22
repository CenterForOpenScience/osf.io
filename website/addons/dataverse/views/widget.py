import httplib as http

from website.addons.dataverse.client import connect_from_settings_or_401, \
    get_dataverse, get_dataset
from website.addons.dataverse.settings import HOST
from website.project.decorators import must_be_contributor_or_public, \
    must_have_addon


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_widget(node_addon, **kwargs):

    node = node_addon.owner
    widget_url = node.api_url_for('dataverse_get_widget_contents')

    ret = {
        'complete': node_addon.complete,
        'widget_url': widget_url,
    }
    ret.update(node_addon.config.to_json())

    return ret, http.OK


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_get_widget_contents(node_addon, **kwargs):

    data = {
        'connected': False,
    }

    if not node_addon.complete:
        return {'data': data}, http.OK

    doi = node_addon.dataset_doi
    alias = node_addon.dataverse_alias

    connection = connect_from_settings_or_401(node_addon.user_settings)
    dataverse = get_dataverse(connection, alias)
    dataset = get_dataset(dataverse, doi)

    if dataset is None:
        return {'data': data}, http.BAD_REQUEST

    dataverse_url = 'http://{0}/dataverse/'.format(HOST) + alias
    dataset_url = 'http://dx.doi.org/' + doi

    data.update({
        'connected': True,
        'dataverse': node_addon.dataverse,
        'dataverseUrl': dataverse_url,
        'dataset': node_addon.dataset,
        'doi': doi,
        'datasetUrl': dataset_url,
        'citation': dataset.citation,
    })
    return {'data': data}, http.OK