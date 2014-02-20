"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from website.project import decorators


@decorators.must_be_valid_project
@decorators.must_be_contributor
def disable_addon(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(http.BAD_REQUEST)

    deleted = node.delete_addon(kwargs['addon'])

    return {'deleted': deleted}


@decorators.must_be_valid_project
@decorators.must_be_contributor_or_public
def get_addon_config(*args, **kwargs):

    user = kwargs['auth'].user
    node = kwargs['node'] or kwargs['project']

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(http.BAD_REQUEST)

    addon = node.get_addon(addon_name)
    if addon is None:
        raise HTTPError(http.BAD_REQUEST)

    return addon.to_json(user)


@must_be_logged_in
def get_addon_user_config(*args, **kwargs):

    user = kwargs['auth'].user

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(http.BAD_REQUEST)

    addon = user.get_addon(addon_name)
    if addon is None:
        raise HTTPError(http.BAD_REQUEST)

    return addon.to_json(user)


def check_file_guid(guid):

    guid_url = '/{0}/'.format(guid._id)
    if not request.path.startswith(guid_url):
        url_split = request.url.split(guid.file_url)
        try:
            guid_url += url_split[1].lstrip('/')
        except IndexError:
            pass
        return guid_url
    return None
