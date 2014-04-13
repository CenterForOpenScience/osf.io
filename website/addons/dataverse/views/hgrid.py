import time
import os
from website.addons.dataverse.client import connect

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus

import hurry


def dataverse_hgrid_data(node_settings, auth, **kwargs):

    node = node_settings.owner

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    # Quit if no study linked
    if node_settings.study_hdl is None or connection is None:
        return []

    name = '{0}/{1}/{2}'.format(
            node_settings.dataverse_username,
            node_settings.dataverse,
            node_settings.study,
    )

    urls = {
        'upload': node.api_url_for('dataverse_upload_file'),
        'fetch': node.api_url_for('dataverse_hgrid_data_contents'),
        'branch': node.api_url_for('dataverse_root_folder_public'),
    }

    return [rubeus.build_addon_root(
        node_settings,
        name,
        urls=urls,
        permissions=auth,
        extra=None,
    )]


# TODO: Can this be combined with dataverse_hgrid_data?
@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_root_folder_public(*args, **kwargs):

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']

    return dataverse_hgrid_data(node_settings, auth=auth)


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_hgrid_data_contents(**kwargs):

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    if node_settings.study_hdl is None or connection is None:
        return []

    info = []

    study = connection.get_dataverses()[node_settings.dataverse_number].get_study_by_hdl(node_settings.study_hdl)

    for f in study.get_files():

        item = {
            rubeus.KIND: rubeus.FILE,
            'name': f.name,
            'urls': {
                    'view': node.web_url_for('dataverse_view_file',
                                             path=f.id),
                    'download': node.api_url_for('dataverse_download_file',
                                                 path=f.id),
                    'delete': node.api_url_for('dataverse_delete_file',
                                               path=f.id),
            },
            'permissions': {
                'view': can_view,
                'edit': can_edit,
            },
            'size': [
                    float(0), # TODO: Implement file size (if possible?),
                    hurry.filesize.size(0, system=hurry.filesize.alternative)
            ],
        }
        info.append(item)

    return info
