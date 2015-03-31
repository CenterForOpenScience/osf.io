# -*- coding: utf-8 -*-

from flask import request

from website.addons.dataverse.client import get_dataset, get_files, \
    get_dataverse, connect_from_settings

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus


def dataverse_hgrid_root(node_addon, auth,  **kwargs):
    node = node_addon.owner
    user_settings = node_addon.user_settings

    default_state = 'published'
    state = 'published' if not node.can_edit(auth) else default_state

    # Quit if no dataset linked
    if not node_addon.complete:
        return []

    connection = connect_from_settings(user_settings)
    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)

    # Quit if doi does not produce a dataset
    if dataset is None:
        return []

    published_files = get_files(dataset, published=True)
    can_edit = node.can_edit(auth)

    # Produce draft version or quit if no published version is available
    if not published_files:
        if can_edit:
            state = 'draft'
        else:
            return []

    dataset_name = node_addon.dataset
    if len(dataset_name) > 23:
        dataset_name = u'{0}...'.format(dataset_name[:20])

    permissions = {
        'edit': can_edit and not node.is_registration,
        'view': node.can_view(auth)
    }

    urls = {
        'publish': node.api_url_for('dataverse_publish_dataset'),
    }

    return [rubeus.build_addon_root(
        node_addon,
        dataset_name,
        urls=urls,
        permissions=permissions,
        dataset=dataset_name,
        doi=dataset.doi,
        dataverse=dataverse.title,
        hasPublishedFiles=bool(published_files),
        state=state,
    )]


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_root_folder_public(node_addon, auth, **kwargs):
    return dataverse_hgrid_root(node_addon, auth=auth)
