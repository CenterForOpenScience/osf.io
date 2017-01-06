from datetime import datetime

import logging

import requests

import api.sso
from framework.auth import User
import framework.discourse
from framework.discourse import common
import framework.logging  # importing this configures the logger, which would not otherwise be configured yet
from framework.sessions import session

logger = logging.getLogger(__name__)

# Safe to call if the user has already been created
def create_user(user, should_save=True):
    """Create a user in Discourse with name equal to the user GUID, copying over all other basic settings
    :param User user: the OSF user to create on Discourse
    :param bool should_save: Whether the function should call user.save()
    :return int: the user ID of the user created
    """
    payload = {
        'external_id': user._id,
        'email': user.username,
        'username': user._id,
        'name': user.fullname,
        'avatar_url': user.profile_image_url()
    }

    data = api.sso.sign_payload(payload)
    try:
        user_id = common.request('post', '/admin/users/sync_sso', data)['id']
        user.discourse_user_id = user_id
        user.discourse_user_created = True
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error creating Discourse user, check your Discourse server')
        return None

    if should_save:
        user.save()

    return user_id

def delete_user(user):
    """Delete the user on Discourse with a username equal to the user GUID,
    including all of their posts on Discourse
    :param User user: the user to delete on Discourse
    :return bool: True if the function finished without internal errors
    """
    if not user.discourse_user_created:
        return True

    try:
        common.request('put', '/admin/users/' + str(user.discourse_user_id) + '/delete_all_posts')
        common.request('delete', '/admin/users/' + str(user.discourse_user_id) + '.json')
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error deleting Discourse user, check your Discourse server')
        return False

    user.discourse_user_id = 0
    user.discourse_user_created = False
    user.save()
    return True

def get_current_osf_user():
    """Return the User currently logged in (to the OSF) or None

    :return User: the currently logged in user to the OSF
    """
    if 'auth_user_id' in session.data:
        user_id = session.data['auth_user_id']
        return User.load(user_id)
    else:
        return None

def get_discourse_username(user=None):
    """Return the Discourse username (OSF guid) of the user, making sure the user exists on Discourse
    Return None if a user is not provided and one is not logged in either
    :param User user: the target user or None to query the currently logged in user
    :return str: the valid Discourse username (the GUID once the user is created) of the user
    """
    if user is None:
        user = get_current_osf_user()
    if user is None:
        return None

    if not user.discourse_user_created:
        create_user(user)
    if not user.discourse_user_created:
        return None
    return user._id

def get_user_apikey(user=None):
    """Return the Discourse user API Key of the user, making sure the user exists on Discourse
    Return None if a user is not provided and one is not logged in either
    :param User user: the target user or None to query the currently logged in user
    :return str: the User's API Key, or None if it could not be retrieved
    """
    if user is None:
        user = get_current_osf_user()
    if user is None:
        return None

    # Use an existing key for up to a day
    if user.discourse_apikey and user.discourse_apikey_date_created:
        key_lifetime = datetime.utcnow() - user.discourse_apikey_date_created
        if key_lifetime.days < 1:
            return user.discourse_apikey

    try:
        result = common.request('post', 'admin/users/' + str(user.discourse_user_id) + '/generate_api_key')
    except (common.DiscourseException, requests.exceptions.ConnectionError):
        logger.exception('Error getting user api key, check your Discourse server')
        return None

    user.discourse_apikey = result['api_key']['key']
    user.discourse_apikey_date_created = datetime.utcnow()
    user.save()

    return user.discourse_apikey

def logout():
    """Logs out the currently logged in user from Discourse, if any"""
    try:
        username = get_discourse_username()
        if username is None:
            return
        common.request('delete', '/session/' + username, username=username)
    except (framework.discourse.DiscourseException, requests.exceptions.ConnectionError):
        # The most expected error would be that the Discourse server might not be running
        logger.exception('Error logging user out of Discourse, check your Discourse server')
