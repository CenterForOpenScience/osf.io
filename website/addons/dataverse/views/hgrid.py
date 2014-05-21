import os

from framework import request
from mako.template import Template
from website.addons.dataverse.client import connect, get_study, get_files

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus


def dataverse_hgrid_root(node_settings, auth, state=None, **kwargs):

    node = node_settings.owner
    state = 'released' if 'files' not in request.referrer or not node.can_edit(auth) \
        else state or 'draft'

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    # Quit if no study linked
    if node_settings.study_hdl is None or connection is None:
        return []

    dataverse = connection.get_dataverse(node_settings.dataverse_alias)
    study = get_study(dataverse, node_settings.study_hdl)

    # Quit if hdl does not produce a study
    if study is None:
        return []

    has_released_files = get_files(study, released=True)
    authorized = node.can_edit(auth)

    # Produce draft version or quit if no released version is available
    if not has_released_files:
        if authorized:
            state = 'draft'
        else:
            return []

    study_name = node_settings.study
    if len(study_name) > 23:
        study_name = '{0}...'.format(study_name[:20])

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
    state_append = dataverse_state_template.render(
        state=state,
        has_released_files=has_released_files,
        authorized=authorized,
    )

    return [rubeus.build_addon_root(
        node_settings,
        study_name,
        urls=urls,
        permissions=permissions,
        extra=state_append,
        study=study_name,
        doi=study.doi,
        dataverse=dataverse.title,
        citation=study.get_citation(),
    )]


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_root_folder_public(**kwargs):

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    state = request.args['state']

    return dataverse_hgrid_root(node_settings, auth=auth, state=state)


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_hgrid_data_contents(**kwargs):

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    state = 'released' if 'files' not in request.referrer or not node.can_edit(auth) \
        else request.args.get('state') or 'draft'

    released = state == 'released'

    can_edit = node.can_edit(auth) and not node.is_registration and not released
    can_view = node.can_view(auth)

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    if node_settings.study_hdl is None or connection is None:
        return []

    dataverse = connection.get_dataverse(node_settings.dataverse_alias)
    study = get_study(dataverse, node_settings.study_hdl)

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
                    'download': node.api_url_for('dataverse_download_file',
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

    return info


dataverse_state_template = Template('''
    <i id="dataverseGetCitation" class="icon-info-sign"></i>
    % if authorized:
        % if has_released_files:
            <select class="dataverse-state-select">
                <option value="draft" ${"selected" if state == "draft" else ""}>Draft</option>
                <option value="released" ${"selected" if state == "released" else ""}>Released</option>
            </select>
        % else:
            [Draft]
        % endif
        % if state == "draft":
            <a id="dataverseReleaseStudy">Release Study</a>
        % endif
    % else:
        [Released]
    % endif
''')