import re

from swiftclient import Connection
from swiftclient import exceptions as swift_exceptions

from framework.exceptions import HTTPError

from addons.swift.provider import SwiftProvider
from addons.swift import settings

def connect_swift(auth_version=None, auth_url=None, access_key=None,
                  user_domain_name=None, secret_key=None,
                  tenant_name=None, project_domain_name=None,
                  node_settings=None, timeout=None):
    """Helper to build an swiftclient.Connection object
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            provider = SwiftProvider(node_settings.external_account)
            auth_url, tenant_name = provider.auth_url, provider.tenant_name
            auth_version = provider.auth_version
            user_domain_name = provider.user_domain_name
            project_domain_name = provider.project_domain_name
            access_key, secret_key = provider.username, provider.password
    if auth_version == '2':
        connection = Connection(auth_version='2',
                                authurl=auth_url,
                                user=access_key,
                                key=secret_key,
                                tenant_name=tenant_name,
                                timeout=timeout)
    else:
        os_options = {'user_domain_name': user_domain_name,
                      'project_domain_name': project_domain_name,
                      'project_name': tenant_name}
        connection = Connection(auth_version='3',
                                authurl=auth_url,
                                user=access_key,
                                key=secret_key,
                                os_options=os_options,
                                timeout=timeout)
    return connection


def get_container_names(node_settings):
    try:
        headers, containers = connect_swift(node_settings=node_settings).get_account()
        return list(map(lambda c: c['name'], containers))
    except swift_exceptions.ClientException as e:
        raise HTTPError(e.http_status)

def validate_container_name(name):
    """Make sure a container name accordings to the naming convention
    https://docs.openstack.org/developer/swift/api/object_api_v1_overview.html
    https://lists.launchpad.net/openstack/msg06956.html
    > Length of container names / Maximum value 256 bytes / Cannot contain the / character.
    """
    validate_name = re.compile('^[^/]+$')
    return (
        len(name) <= 256 and bool(validate_name.match(name))
    )


def create_container(node_settings, container_name):
    return connect_swift(node_settings=node_settings).put_container(container_name)


def container_exists(auth_version, auth_url, access_key, user_domain_name,
                     secret_key, tenant_name, project_domain_name,
                     container_name):
    """Tests for the existance of a container and if the user
    can access it with the given properties
    """
    if not container_name:
        return False

    try:
        # Will raise an exception if container_name doesn't exist
        connect_swift(auth_version, auth_url, access_key, user_domain_name,
                      secret_key, tenant_name,
                      project_domain_name).head_container(container_name)
    except swift_exceptions.ClientException as e:
        if e.http_status not in (301, 302):
            return False
    return True


def can_list(auth_version, auth_url, access_key, user_domain_name, secret_key,
             tenant_name, project_domain_name):
    """Return whether or not a user can list
    all containers accessable by this keys
    """
    if not (auth_version and auth_url and access_key and secret_key and tenant_name):
        return False

    try:
        connect_swift(auth_version, auth_url, access_key, user_domain_name,
                      secret_key, tenant_name, project_domain_name,
                      timeout=settings.TEST_TIMEOUT).get_account()
    except swift_exceptions.ClientException:
        return False
    return True

def get_user_info(auth_version, auth_url, access_key, user_domain_name,
                  secret_key, tenant_name, project_domain_name):
    """Returns an Swift User with .display_name and .id, or None
    """
    if not (auth_version and auth_url and access_key and secret_key and tenant_name):
        return None

    if auth_version == '2':
        return {'display_name': '{}@{} on {}'.format(access_key, tenant_name, auth_url),
                'id': '{}-{}-{}'.format(auth_url, tenant_name, access_key)}
    elif auth_version == '3':
        if not (user_domain_name and project_domain_name):
            return None
        return {'display_name': '{}@{} {}@{} on {}'.format(access_key,
                                                           user_domain_name,
                                                           tenant_name,
                                                           project_domain_name,
                                                           auth_url),
                'id': '{}-{}-{}-{}-{}'.format(auth_url, tenant_name,
                                              project_domain_name,
                                              access_key, user_domain_name)}
    else:
        return None
