import re
import json
import urllib
import urllib2
import httplib

from framework.exceptions import HTTPError
from website.util import web_url_for

def get_project_list(user_settings):
    projects = None
    base_url = user_settings.sharelatex_url
    query_args = {'auth_token': user_settings.auth_token}
    encoded_args = urllib.urlencode(query_args)
    url = '{}/api/v1/project?{}'.format(base_url, encoded_args)
    projects = json.load(urllib2.urlopen(url))

    if not projects:
        raise HTTPError(httplib.FORBIDDEN)

    return projects

def get_project_names(user_settings):
    projects = get_project_list(user_settings)
    return [project['name'] for project in projects]

def validate_project_name(name):
    validate_name = re.compile('^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$')
    return bool(validate_name.match(name))

def new_project(user_settings, project_name, location=''):
    return ''

def create_project():
    return ''

def project_exists(sharelatex_url, auth_token, project_name):
    """Tests for the existance of a project and if the user
    can access it with the given keys
    """
    if not project_name:
        return False

    return True

def can_list(sharelatex_url, auth_token):
    """Return whether or not a user can list
    all projects accessable by this keys
    """
    if not (sharelatex_url and auth_token):
        return False

    return True

def serialize_urls(node_addon, user):
    node = node_addon.owner
    user_settings = node_addon.user_settings

    result = {
        'new_project': node.api_url_for('sharelatex_new_project'),
        'import_auth': node.api_url_for('sharelatex_node_import_auth'),
        'create_auth': node.api_url_for('sharelatex_authorize_node'),
        'deauthorize': node.api_url_for('sharelatex_delete_node_settings'),
        'project_list': node.api_url_for('sharelatex_get_project_list'),
        'set_project': node.api_url_for('sharelatex_get_node_settings'),
        'settings': web_url_for('user_addons'),
        'files': node.web_url_for('collect_file_trees'),
    }
    if user_settings:
        result['owner'] = user_settings.owner.profile_url
    return result
