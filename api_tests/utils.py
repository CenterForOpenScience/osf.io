from urlparse import urlparse
from addons.osfstorage import settings as osfstorage_settings
from framework.auth.core import Auth

def create_test_file(node, user, filename='test_file', create_guid=True):
    osfstorage = node.get_addon('osfstorage')
    root_node = osfstorage.get_root()
    test_file = root_node.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 1337,
        'contentType': 'img/png'
    }).save()

    root_node.add_log(
        'osf_storage_file_added',
        auth=Auth(user),
        params={
            'node': root_node._id,
            'project': root_node.parent_id,
            'path': test_file.materialized_path,
            'params_file':  '/project/{}/files/osfstorage/{}/'.format(root_node._id, test_file._id)
        },
    )
    root_node.save()

    return test_file

def urlparse_drop_netloc(url):
    url = urlparse(url)
    if url[4]:
        return url[2] + '?' + url[4]
    return url[2]
