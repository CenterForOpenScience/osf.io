# -*- coding: utf-8 -*-
import logging

from framework import session, create_session
from framework import goback
from framework import bcrypt
from framework.auth.exceptions import (
    DuplicateEmailError, LoginNotAllowedError, PasswordIncorrectError
)

from .core import User, Auth
from .core import get_user, get_current_user, get_api_key, get_current_node


logger = logging.getLogger(__name__)


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


def login(username, password):
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
            elif not user.is_claimed:
                raise LoginNotAllowedError('User is not claimed.')
            else:
                return authenticate(user, response=goback())
    raise PasswordIncorrectError('Incorrect password attempt.')


def logout():
    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname']:
        # todo leave username so login page can persist probable id
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
    elif not user.is_registered: # User is in db but not registered
        user.add_email_verification(username)
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
