from blinker import ANY
from enum import Enum
from urllib.parse import urlparse
from contextlib import contextmanager
from addons.osfstorage import settings as osfstorage_settings


def create_test_file(target, user, filename='test_file', create_guid=True, size=1337, sha256=None):
    osfstorage = target.get_addon('osfstorage')
    root_node = osfstorage.get_root()
    test_file = root_node.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        'bucket': 'us-bucket',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': size,
        'contentType': 'img/png',
        'sha256': sha256,
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


class UserRoles(Enum):
    UNAUTHENTICATED = 0
    NONCONTRIB = 1
    MODERATOR = 2
    READ_USER = 3
    WRITE_USER = 4
    ADMIN_USER = 5

    @classmethod
    def contributor_roles(cls, include_moderator=False):
        base_roles = [cls.READ_USER, cls.WRITE_USER, cls.ADMIN_USER]
        if include_moderator:
            return [cls.MODERATOR, *base_roles]
        return base_roles

    @classmethod
    def noncontributor_roles(cls):
        return [cls.UNAUTHENTICATED, cls.NONCONTRIB, cls.MODERATOR]

    @classmethod
    def write_roles(cls):
        return [cls.WRITE_USER, cls.ADMIN_USER]

    @classmethod
    def excluding(cls, *excluded_roles):
        return [role for role in cls if role not in excluded_roles]

    def get_permissions_string(self):
        if self is UserRoles.READ_USER:
            return 'read'
        if self is UserRoles.WRITE_USER:
            return 'write'
        if self is UserRoles.ADMIN_USER:
            return 'admin'
        return None
