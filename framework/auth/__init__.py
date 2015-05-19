# -*- coding: utf-8 -*-

from framework.sessions import session, create_session
from framework import bcrypt
from framework.auth.exceptions import (
    DuplicateEmailError,
    TwoFactorValidationError,
)
from framework.flask import redirect

from website import settings

from .core import User, Auth
from .core import get_user


__all__ = [
    'get_display_name',
    'Auth',
    'User',
    'get_user',
    'check_password',
    'authenticate',
    'logout',
    'register_unconfirmed',
]

def get_display_name(username):
    """Return the username to display in the navbar. Shortens long usernames."""
    if len(username) > 40:
        return '%s...%s' % (username[:20].strip(), username[-15:].strip())
    return username


# check_password(actual_pw_hash, given_password) -> Boolean
check_password = bcrypt.check_password_hash


def authenticate(user, access_token, response):
    data = session.data if session._get_current_object() else {}
    data.update({
        'auth_user_username': user.username,
        'auth_user_id': user._primary_key,
        'auth_user_fullname': user.fullname,
        'auth_user_access_token': access_token,
    })
    response = create_session(response, data=data)
    return response

def authenticate_two_factor(user):
    """Begins authentication for two factor auth users

    :param user: User to be authenticated
    :return: Response object directed to two-factor view
    """
    data = session.data if session._get_current_object() else {}
    data.update({'two_factor_auth': {
        'auth_user_username': user.username,
        'auth_user_id': user._primary_key,
        'auth_user_fullname': user.fullname,
    }})

    # Redirect to collect two factor code from user
    next_url = data.get('next_url', False)

    # NOTE: Avoid circular import /hrybacki
    from website.util import web_url_for
    if next_url:
        response = redirect(web_url_for('two_factor', next=next_url))
    else:
        response = redirect(web_url_for('two_factor'))
    response = create_session(response, data)
    return response


def user_requires_two_factor_verification(user):
    """Returns if user has two factor auth enabled

    :param user: User to be checked
    :return: True if user has two factor auth enabled
    """
    if 'twofactor' in settings.ADDONS_REQUESTED:
        two_factor_auth = user.get_addon('twofactor')
        # TODO refactor is_confirmed as is_enabled /hrybacki
        return two_factor_auth and two_factor_auth.is_confirmed
    return False


def verify_two_factor(user_id, two_factor_code):
    """Verifies user two factor authentication for specified user

    :param user_id: ID for user attempting login
    :param two_factor_code: two factor code for authentication
    :return: Response object
    """
    user = User.load(user_id)
    two_factor_auth = user.get_addon('twofactor')
    if two_factor_auth and not two_factor_auth.verify_code(two_factor_code):
        # Raise error if incorrect code is submitted
        raise TwoFactorValidationError('Two-Factor auth does not match.')

    # Update session field verifying two factor and delete key used for auth
    session.data.update(session.data['two_factor_auth'])
    del session.data['two_factor_auth']

    next_url = session.data.get('next_url', False)
    if next_url:
        response = redirect(next_url)
    else:
        # NOTE: avoid circular import /hrybacki
        from website.util import web_url_for
        response = redirect(web_url_for('dashboard'))
    return response


def logout():
    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname', 'auth_user_access_token']:
        try:
            del session.data[key]
        except KeyError:
            pass
    return True


def register_unconfirmed(username, password, fullname):
    user = get_user(email=username)
    if not user:
        user = User.create_unconfirmed(username=username,
            password=password,
            fullname=fullname)
        user.save()
    elif not user.is_registered:  # User is in db but not registered
        user.add_unconfirmed_email(username)
        user.set_password(password)
        user.fullname = fullname
        user.update_guessed_names()
        user.save()
    else:
        raise DuplicateEmailError('User {0!r} already exists'.format(username))
    return user
