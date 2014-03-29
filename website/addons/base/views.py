"""

"""

import httplib as http
from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from website.project import decorators


@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def disable_addon(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(http.BAD_REQUEST)

    deleted = node.delete_addon(addon_name, auth)

    return {'deleted': deleted}


@must_be_logged_in
def get_addon_user_config(**kwargs):

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
