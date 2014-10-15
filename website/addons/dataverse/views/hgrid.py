# -*- coding: utf-8 -*-

import os

from flask import request
from mako.template import Template

from website.addons.dataverse.client import get_study, get_files, \
    get_dataverse, connect_from_settings

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.settings import BASE_PATH
from website.util import rubeus


def dataverse_hgrid_root(node_addon, auth, state=None, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    default_state = 'released'
    state = 'released' if not node.can_edit(auth) else state or default_state

    connection = connect_from_settings(user_settings)

    # Quit if no study linked
    if node_addon.study_hdl is None or connection is None:
        return []

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    study = get_study(dataverse, node_addon.study_hdl)

    # Quit if hdl does not produce a study
    if study is None:
        return []

    released_files = get_files(study, released=True)
    authorized = node.can_edit(auth)

    # Produce draft version or quit if no released version is available
    if not released_files:
        if authorized:
            state = 'draft'
        else:
            return []

    study_name = node_addon.study
    if len(study_name) > 23:
        study_name = u'{0}...'.format(study_name[:20])

    permissions = {
        'edit': node.can_edit(auth) and not node.is_registration and state == 'draft',
        'view': node.can_view(auth)
    }

    urls = {
        'upload': node.api_url_for('dataverse_upload_file'),
        'fetch': node.api_url_for('dataverse_hgrid_data_contents', state=state),
        'state': node.api_url_for('dataverse_root_folder_public'),
        'release': node.api_url_for('dataverse_release_study'),
    }

    # Determine default state / selection permissions
    template_file = os.path.join(
        BASE_PATH, 'addons/dataverse/templates/dataverse_state_template.mako'
    )
    dataverse_state_template = Template(filename=template_file)
    state_append = dataverse_state_template.render(
        state=state,
        has_released_files=bool(released_files),
        authorized=authorized,
    )
    buttons = [rubeus.build_addon_button(
        '<i class="icon-globe"></i> Release Study',
        'releaseStudy')] if state == 'draft' else None

    return [rubeus.build_addon_root(
        node_addon,
        study_name,
        urls=urls,
        permissions=permissions,
        extra=state_append,
        buttons=buttons,
        study=study_name,
        doi=study.doi,
        dataverse=dataverse.title,
        citation=study.citation,
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
    default_state = 'released'
    state = 'released' if not node.can_edit(auth) else state or default_state

    released = state == 'released'

    can_edit = node.can_edit(auth) and not node.is_registration and not released
    can_view = node.can_view(auth)

    connection = connect_from_settings(user_settings)

    if node_addon.study_hdl is None or connection is None:
        return []

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    study = get_study(dataverse, node_addon.study_hdl)

    # Quit if hdl does not produce a study
    if study is None:
        return []

    info = []

    for f in get_files(study, released):

        item = {
            'addon': 'dataverse',
            rubeus.KIND: rubeus.FILE,
            'name': f.name,
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
