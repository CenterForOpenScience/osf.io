from website.project.decorators import must_be_contributor_or_public, must_have_addon
from website.addons.s3.api import S3Wrapper
from website.addons.s3.utils import wrapped_key_to_json_new
from framework import request

def s3_dummy_folder(node_settings, user, parent=None, **kwargs):

    # Quit if no bucket
    if not node_settings.bucket or not node_settings.node_auth:
        return

    node = node_settings.owner

    rv = {
        'addonName': 'Amazon Simple Storage Service',
        'maxFilesize': node_settings.config.max_file_size,
        'uid': 's3:{0}'.format(node_settings._id),
        'name': 'Amazon S3: {0}'.format(
            node_settings.bucket
        ),
        'parent_uid': parent or 'null',
        'type': 'folder',
        'can_view': node.can_view(user),
        'can_edit': node.can_edit(user) and not node.is_registration,
        'permission': node.can_edit(user) and not node.is_registration,
        'lazyLoad': node.api_url + 's3/hgrid/',
    }

    return rv


#TODO Polish me... A LOT
#Again... Lazy loading?
#Key prefixing!
@must_be_contributor_or_public
@must_have_addon('osffiles', 'node')
def s3_hgrid_data_contents(*args, **kwargs):

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    s3_node_settings = node.get_addon('s3')
    user = kwargs['user']
    parent = request.args.get('parent', 'null')

    can_edit = node.can_edit(user) and not node.is_registration
    can_view = node.can_view(user)

    s3wrapper = S3Wrapper.from_addon(s3_node_settings)

    files = []
    if 's3:' in parent:
        key_list = s3wrapper.get_wrapped_keys_in_dir()
        key_list.extend(s3wrapper.get_wrapped_directories_in_dir())
    else:
        key_list = s3wrapper.get_wrapped_keys_in_dir(parent)
        key_list.extend(s3wrapper.get_wrapped_directories_in_dir(parent))

    for key in key_list:#parent):
        temp_file = wrapped_key_to_json_new(key, node.api_url, parent or 'null')
        temp_file['lazyLoad'] = node_settings.owner.api_url + 's3/hgrid/',
        temp_file['can_edit'] = can_edit
        temp_file['permission'] = can_edit
        files.append(temp_file)

    return files
