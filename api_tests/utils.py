from blinker import ANY
from future.moves.urllib.parse import urlparse
from contextlib import contextmanager
from addons.osfstorage import settings as osfstorage_settings


def create_test_file(target, user, filename='test_file', create_guid=True, size=1337):
    osfstorage = target.get_addon('osfstorage')
    root_node = osfstorage.get_root()
    test_file = root_node.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': size,
        'contentType': 'img/png'
    }).save()
    return test_file


def create_test_preprint_file(target, user, filename='test_file', create_guid=True, size=1337):
    root_folder = target.root_folder
    test_file = root_folder.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': size,
        'contentType': 'img/png'
    }).save()
    return test_file


def urlparse_drop_netloc(url):
    url = urlparse(url)
    if url[4]:
        return url[2] + '?' + url[4]
    return url[2]


@contextmanager
def disconnected_from_listeners(signal):
    """Temporarily disconnect all listeners for a Blinker signal."""
    listeners = list(signal.receivers_for(ANY))
    for listener in listeners:
        signal.disconnect(listener)
    yield
    for listener in listeners:
        signal.connect(listener)

def only_supports_methods(view, expected_methods):
    if isinstance(view.__class__, type):
        view = view()
    expected_methods.append('OPTIONS')
    return set(expected_methods) == set(view.allowed_methods)
