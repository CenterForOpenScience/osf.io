# -*- coding: utf-8 -*-

from requests.exceptions import SSLError

from website.addons.dataverse.client import get_dataset, get_files, \
    get_dataverse, connect_from_settings

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus


def dataverse_hgrid_root(node_addon, auth, **kwargs):
    node = node_addon.owner
    user_settings = node_addon.user_settings

    default_version = 'latest-published'
    version = 'latest-published' if not node.can_edit(auth) else default_version

    # Quit if no dataset linked
    if not node_addon.complete:
        return []

    can_edit = node.can_edit(auth)

    permissions = {
        'edit': can_edit and not node.is_registration,
        'view': node.can_view(auth)
    }

    try:
        connection = connect_from_settings(user_settings)
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
        'publishBoth': node.api_url_for('dataverse_publish_both')
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


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_root_folder_public(node_addon, auth, **kwargs):
    return dataverse_hgrid_root(node_addon, auth=auth)
