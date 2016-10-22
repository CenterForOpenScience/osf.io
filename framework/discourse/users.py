from .common import request

import api.sso
from framework.sessions import session
from framework.auth import User
from datetime import datetime

# Safe to call if the user has already been created
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

def get_current_user():
    if 'auth_user_id' in session.data:
        user_id = session.data['auth_user_id']
        return User.load(user_id)
    else:
        return None

def get_username(user=None):
    if user is None:
        user = get_current_user()
    if user is None:
        return None

    if not user.discourse_user_created:
        create_user(user)
    return user._id

def get_user_id(user=None):
    if user is None:
        user = get_current_user()
    if user is None:
        return None

    if not user.discourse_user_created:
        create_user(user)
    return user.discourse_user_id

def get_user_apikey(user=None):
    if user is None:
        user = get_current_user()

    # Use an existing key for up to a day
    if user.discourse_apikey_date_created:
        key_lifetime = datetime.now() - user.discourse_apikey_date_created
        if user.discourse_apikey and key_lifetime.days < 1:
            return user.discourse_apikey

    user_id = get_user_id(user)
    result = request('post', 'admin/users/' + str(user_id) + '/generate_api_key')
    user.discourse_apikey = result['api_key']['key']
    user.discourse_apikey_date_created = datetime.now()
    user.save()

    return user.discourse_apikey

def logout():
    username = get_username()
    if username is None:
        return
    return request('delete', '/session/' + username, username=username)
