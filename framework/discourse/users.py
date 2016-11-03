from .common import request

import api.sso
from framework.sessions import session
from framework.auth import User
from datetime import datetime

# Safe to call if the user has already been created
def create_user(user, should_save=True):
    """Create a user in Discourse with name equal to the user GUID, copying over all other basic settings
    :param User user: the OSF user to create on Discourse
    :param bool should_save: Whether the function should call user.save()
    :return int: the user ID of the user created
    """
    payload = {}
    payload['external_id'] = user._id
    payload['email'] = user.username
    payload['username'] = user._id
    payload['name'] = user.fullname
    payload['avatar_url'] = user.profile_image_url()

    data = api.sso.sign_payload(payload)
    user_id = request('post', '/admin/users/sync_sso', data)['id']

    user.discourse_user_id = user_id
    user.discourse_user_created = True

    if should_save:
        user.save()

    return user_id

def delete_user(user):
    """Delete the user on Discourse with a username equal to the user GUID,
    including all of their posts on Discourse
    :param User user: the user to delete on Discourse
    """
    if not user.discourse_user_created:
        return

    request('put', '/admin/users/' + str(user.discourse_user_id) + '/delete_all_posts')
    request('delete', '/admin/users/' + str(user.discourse_user_id) + '.json')

    user.discourse_user_id = 0
    user.discourse_user_created = False
    user.save()

def get_current_user():
    """Return the User currently logged in or None

    :return User: the currently logged in user
    """
    if 'auth_user_id' in session.data:
        user_id = session.data['auth_user_id']
        return User.load(user_id)
    else:
        return None

def get_username(user=None):
    """Return the Discourse username (OSF guid) of the user, making sure the user exists on Discourse
    Return None if a user is not provided and one is not logged in either
    :param User user: the target user or None to query the currently logged in user
    :return str: the valid Discourse username (the GUID once the user is created) of the user
    """
    if user is None:
        user = get_current_user()
    if user is None:
        return None

    if not user.discourse_user_created:
        create_user(user)
    return user._id

def get_user_id(user=None, should_save=True):
    """Return the Discourse user ID of the user, making sure the user exists on Discourse
    Return None if a user is not provided and one is not logged in either
    :param User user: the target user or None to query the currently logged in user
    :param bool should_save: Whether the function should call user.save() if the user is created
    :return int: the Discourse user ID
    """
    if user is None:
        user = get_current_user()
    if user is None:
        return None

    if not user.discourse_user_created:
        create_user(user, should_save)
    return user.discourse_user_id

def get_user_apikey(user=None):
    """Return the Discourse user API Key of the user, making sure the user exists on Discourse
    Return None if a user is not provided and one is not logged in either
    :param User user: the target user or None to query the currently logged in user
    :return str: the User's API Key
    """
    if user is None:
        user = get_current_user()
    if user is None:
        return None

    # Use an existing key for up to a day
    if user.discourse_apikey_date_created:
        key_lifetime = datetime.now() - user.discourse_apikey_date_created
        if user.discourse_apikey and key_lifetime.days < 1:
            return user.discourse_apikey

    user_id = get_user_id(user, False)
    result = request('post', 'admin/users/' + str(user_id) + '/generate_api_key')
    user.discourse_apikey = result['api_key']['key']
    user.discourse_apikey_date_created = datetime.now()
    user.save()

    return user.discourse_apikey

def logout():
    """Logs out the currently logged in user from Discourse, if any"""
    username = get_username()
    if username is None:
        return
    request('delete', '/session/' + username, username=username)
