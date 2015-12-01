# -*- coding: utf-8 -*-

from flask import request
from framework.exceptions import HTTPError
from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_addon_authorizer

def view_dryad_repo(node_settings, auth, **kwargs):
    pass


def dryad_addon_folder(node_settings, auth, **kwargs):    
    # Quit if no dataset linked
    if not node_settings.complete:
        return []

    node = node_settings.owner

    urls = {
        #'upload': node_settings.owner.api_url + 'dryad/file/' + node_settings.dryad_doi,
        #'fetch': node_settings.owner.api_url + 'dryad/hgrid/' + node_settings.dryad_doi,
        #'branch': node_settings.owner.api_url + 'dryad/hgrid/root/',
        #'zip': node_settings.owner.api_url + 'dryad/zipball/' + node_settings.dryad_doi,
        'repo': 'http://api.datadryad.org/mn/object/'+node_settings.dryad_doi
    }
    

    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder_name,
        doi=node_settings.dryad_doi,
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    print root

    return [root]
    
"""

    try:
        connection = connect_from_settings(node_addon)
        dataverse = get_dataverse(connection, node_addon.dataverse_alias)
        dataset = get_dataset(dataverse, node_addon.dataset_doi)
    except SSLError:
        return [rubeus.build_addon_root(
            node_addon,
            node_addon.dataset,
            permissions=permissions
        )]

    # Quit if doi does not produce a dataset
    if dataset is None:
        return []

    published_files = get_files(dataset, published=True)

    # Produce draft version or quit if no published version is available
    if not published_files:
        if can_edit:
            version = 'latest'
        else:
            return []

    urls = {
        'publish': node.api_url_for('dataverse_publish_dataset'),
    }

    return [rubeus.build_addon_root(
        node_addon,
        node_addon.dataset,
        urls=urls,
        permissions=permissions,
        dataset=node_addon.dataset,
        doi=dataset.doi,
        dataverse=dataverse.title,
        hasPublishedFiles=bool(published_files),
        dataverseIsPublished=dataverse.is_published,
        version=version,
    )]

"""



@must_be_contributor_or_public
@must_have_addon('dryad', 'node')
def dryad_root_folder_public(node_addon, auth, **kwargs):
    return dryad_hgrid_root(node_addon, auth=auth)