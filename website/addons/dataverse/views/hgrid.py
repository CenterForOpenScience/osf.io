# -*- coding: utf-8 -*-

import os

from flask import request

from website.addons.dataverse.client import get_dataset, get_files, \
    get_dataverse, connect_from_settings

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus


def dataverse_hgrid_root(node_addon, auth, state=None, **kwargs):
    node = node_addon.owner
    user_settings = node_addon.user_settings

    default_state = 'published'
    state = 'published' if not node.can_edit(auth) else state or default_state

    connection = connect_from_settings(user_settings)

    # Quit if no dataset linked
    if node_addon.dataset_doi is None or connection is None:
        return []

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)

    # Quit if hdl does not produce a dataset
    if dataset is None:
        return []

    published_files = get_files(dataset, published=True)
    authorized = node.can_edit(auth)

    # Produce draft version or quit if no published version is available
    if not published_files:
        if authorized:
            state = 'draft'
        else:
            return []

    dataset_name = node_addon.dataset
    if len(dataset_name) > 23:
        dataset_name = u'{0}...'.format(dataset_name[:20])

    permissions = {
        'edit': node.can_edit(auth) and not node.is_registration,
        'view': node.can_view(auth)
    }

    urls = {
        'upload': node.api_url_for('dataverse_upload_file'),
        'fetch': node.api_url_for('dataverse_hgrid_data_contents', state=state),
        'state': node.api_url_for('dataverse_root_folder_public'),
        'publish': node.api_url_for('dataverse_publish_dataset'),
    }

    buttons = [rubeus.build_addon_button(
        '<i class="fa fa-globe"></i> Publish Dataset',
        'publishDataset')] if state == 'draft' else None

    return [rubeus.build_addon_root(
        node_addon,
        dataset_name,
        urls=urls,
        permissions=permissions,
        buttons=buttons,
        dataset=dataset_name,
        doi=dataset.doi,
        dataverse=dataverse.title,
        citation=dataset.citation,
        hasPublishedFiles=bool(published_files),
        state=state,
    )]


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_root_folder_public(node_addon, auth, **kwargs):
    state = request.args['state']
    return dataverse_hgrid_root(node_addon, auth=auth, state=state)


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_hgrid_data_contents(node_addon, auth, **kwargs):
    node = node_addon.owner
    user_settings = node_addon.user_settings

    state = request.args.get('state')
    default_state = 'published'
    state = 'published' if not node.can_edit(auth) else state or default_state

    published = state == 'published'

    can_edit = node.can_edit(auth) and not node.is_registration and not published
    can_view = node.can_view(auth)

    connection = connect_from_settings(user_settings)

    if node_addon.dataset_doi is None or connection is None:
        return []

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)

    # Quit if hdl does not produce a dataset
    if dataset is None:
        return []

    info = []

    for f in get_files(dataset, published):

        item = {
            'addon': 'dataverse',
            'provider': 'dataverse',
            rubeus.KIND: 'file',
            'name': f.name,
            'path': f.name,
            'file_id': f.id,
            'ext': os.path.splitext(f.name)[1],
            'urls': {
                'view': node.web_url_for('dataverse_view_file',
                                         path=f.id),
                'download': node.web_url_for('dataverse_download_file',
                                             path=f.id),
                'delete': node.api_url_for('dataverse_delete_file',
                                           path=f.id),
            },
            'permissions': {
                'view': can_view,
                'edit': can_edit,
            },
        }
        info.append(item)

    return {'data': info}
