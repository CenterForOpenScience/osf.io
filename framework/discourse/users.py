from .common import *

import api.sso
from framework.sessions import session
from framework.auth import User

def create_user(user):
    payload = {}
    payload['external_id'] = user._id
    payload['email'] = user.username
    payload['username'] = user._id
    payload['name'] = user.fullname
    payload['avatar_url'] = user.profile_image_url()

    data = api.sso.sign_payload(payload)
    result = request('post', '/admin/users/sync_sso', data)

    user.discourse_user_id = result['id']
    user.discourse_user_created = True
    user.save()

    return result

def delete_user(user):
    if not user.discourse_user_created:
        return

    request('put', '/admin/users/' + str(user.discourse_user_id) + '/delete_all_posts')
    result = request('delete', '/admin/users/' + str(user.discourse_user_id) + '.json')

    user.discourse_user_id = 0
    user.discourse_user_created = False
    user.save()

    return result

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
    return request('delete', '/session/' + username)
