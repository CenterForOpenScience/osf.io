# -*- coding: utf-8 -*-

from framework.sessions import session, create_session, goback
from framework import bcrypt
from framework.auth.exceptions import (
    DuplicateEmailError,
    LoginDisabledError,
    LoginNotAllowedError,
    PasswordIncorrectError,
    TwoFactorValidationError,
)

from .core import User, Auth
from .core import get_user

from website import settings

__all__ = [
    'get_display_name',
    'Auth',
    'User',
    'get_user',
    'check_password',
    'authenticate',
    'login',
    'logout',
    'register_unconfirmed',
    'register',
]

def get_display_name(username):
    """Return the username to display in the navbar. Shortens long usernames."""
    if len(username) > 40:
        return '%s...%s' % (username[:20].strip(), username[-15:].strip())
    return username


# check_password(actual_pw_hash, given_password) -> Boolean
check_password = bcrypt.check_password_hash


def authenticate(user, response):
    data = session.data if session._get_current_object() else {}
    data.update({
        'auth_user_username': user.username,
        'auth_user_id': user._primary_key,
        'auth_user_fullname': user.fullname,
    })
    response = create_session(response, data=data)
    return response


def login(username, password, two_factor=None):
    """View helper function for logging in a user. Either authenticates a user
    and returns a ``Response`` or raises an ``AuthError``.

    :raises: AuthError on a bad login
    :returns: Redirect response to settings page on successful login.
    """
    username = username.strip().lower()
    password = password.strip()
    if username and password:
        user = get_user(
            username=username,
            password=password
        )
        if user:
            if not user.is_registered:
                raise LoginNotAllowedError('User is not registered.')

            if not user.is_claimed:
                raise LoginNotAllowedError('User is not claimed.')

            if user.is_disabled:
                raise LoginDisabledError('User is disabled.')

            if 'twofactor' in settings.ADDONS_REQUESTED:
                tfa = user.get_addon('twofactor')
                if tfa and tfa.is_confirmed and not tfa.verify_code(two_factor):
                    raise TwoFactorValidationError('Two-Factor auth does not match.')

            return authenticate(user, response=goback())
    raise PasswordIncorrectError('Incorrect password attempt.')

def logout():
    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname']:
        try:
            del session.data[key]
        except KeyError:
            pass
    return True


def register_unconfirmed(username, password, fullname):
    user = get_user(username=username)
    if not user:
        user = User.create_unconfirmed(username=username,
            password=password,
            fullname=fullname)
        user.save()
    elif not user.is_registered:  # User is in db but not registered
        user.add_email_verification(username)
        user.set_password(password)
        user.fullname = fullname
        user.update_guessed_names()
        user.save()
    else:
        raise DuplicateEmailError('User {0!r} already exists'.format(username))
    return user


def register(username, password, fullname):
    user = get_user(username=username)
    if not user:
        user = User.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
    user.registered = True
    user.date_confirmed = user.date_registered
    user.emails.append(username)
    user.save()
    return user
