from website.project.decorators import must_be_contributor_or_public, must_have_addon
from website.addons.s3.api import S3Wrapper
from website.addons.s3.utils import wrapped_key_to_json
from framework import request
from urllib import unquote


def s3_hgrid_data(node_settings, user, parent=None, **kwargs):

    # Quit if no bucket
    if not node_settings.bucket or not node_settings.user_settings or not node_settings.user_settings.has_auth:
        return

    node = node_settings.owner

    rv = {
        'addon': 'Amazon Simple Storage Service',
        'name': 'Amazon S3: {0}'.format(
            node_settings.bucket
        ),
        'kind': 'folder',
        'permissions': {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        },
        'urls': {
            'fetch': node.api_url + 's3/hgrid/',
            'upload': node.api_url + 's3/upload/'
        },
        'accept': {
            'maxSize': node_settings.config.max_file_size,
            'extensions': node_settings.config.accept_extensions
        }
    }

    return rv


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_hgrid_data_contents(*args, **kwargs):

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    s3_node_settings = node.get_addon('s3')
    user = kwargs['user']
    path = unquote(kwargs.get('path', None)) + '/' if kwargs.get('path', None) else None

    can_edit = node.can_edit(user) and not node.is_registration
    can_view = node.can_view(user)

    s3wrapper = S3Wrapper.from_addon(s3_node_settings)

    files = []

    key_list = s3wrapper.get_wrapped_keys_in_dir(path)
    key_list.extend(s3wrapper.get_wrapped_directories_in_dir(path))

    for key in key_list:
        temp_file = wrapped_key_to_json(
            key, node.api_url, node.url)
        temp_file['addon'] = 's3'
        temp_file['permissions'] = {
            'edit': can_edit,
            'view': can_view
        }
        files.append(temp_file)

    return files


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_dummy_folder(*args, **kwargs):
    node_settings = kwargs['node_addon']
    user = get_current_user()
    data = request.args.to_dict()

    parent = data.pop('parent', 'null')

    return s3_hgrid_data(node_settings, user, parent, contents=False, **data)
