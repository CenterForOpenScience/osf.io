from . import *

from website import settings

import api.sso
from framework.sessions import session
from framework.auth import User

import requests
from furl import furl

def create_user(user):
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/users/sync_sso')

    payload = {}
    payload['external_id'] = user._id
    payload['email'] = user.username
    payload['username'] = user._id
    payload['name'] = user.fullname
    payload['avatar_url'] = user.profile_image_url()

    url.args = api.sso.sign_payload(payload)
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.post(url.url)

    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to user create/sync request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    user.discourse_user_id = result.json()['id']
    user.discourse_user_created = True
    user.save()

    return result.json()

def delete_user(user):
    if not user.discourse_user_created:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/users/' + str(user.discourse_user_id))
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.delete(url.url)

    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to user delete request '
                                 + url.url + ' with '
                                 + str(result.status_code) + ' ' + result.text)

    user.discourse_user_id = 0
    user.discourse_user_created = False
    user.save()

def get_username(user=None):
    if user is None:
        if 'auth_user_id' in session.data:
            user_id = session.data['auth_user_id']
            user = User.load(user_id)
        else:
            return None

    if not user.discourse_user_created:
        create_user(user)
    return user._id

def logout():
    username = get_username()
    if username is None:
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/session/' + username)
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = username

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to logout request with '
                                 + str(result.status_code) + ' ' + result.text)
