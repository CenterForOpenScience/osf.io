
# TODO: Figure out where this is called and what it does.


def dataverse_hgrid_data(node_settings, user, contents=False, **kwargs):

    # Quit if no study linked
    dataverse_user = node_settings.user_settings
    if node_settings.study_hdl != "None":
        return

    connection = dataverse_user.connect(node_settings.dataverse_username, node_settings.dataverse_password)

    can_edit = True # TODO: Validate user

    rv = {
        'addon': 'Dataverse',
        'name': 'Dataverse: {0}/{1} {2}'.format(
            node_settings.dataverse_username, node_settings.dataverse, node_settings.study,
        ),
        'kind': 'folder',
        'urls': {
        },
        'permissions': {
            'view': True,
            'edit': can_edit,
        },
        'accept': {
            'maxSize': node_settings.config.max_file_size,
            'extensions': node_settings.config.accept_extensions,
        }
    }

    return rv

