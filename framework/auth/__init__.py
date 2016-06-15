# -*- coding: utf-8 -*-

from datetime import datetime
import uuid

from modularodm import Q

from framework import bcrypt
from framework.auth import signals
from framework.auth.exceptions import DuplicateEmailError
from framework.sessions import session, create_session, Session
from .core import User, Auth
from .core import get_user, generate_verification_key


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
    user.date_last_login = datetime.utcnow()
    user.clean_email_verifications()
    user.update_affiliated_institutions_by_email_domain()
    user.save()
    response = create_session(response, data=data)
    return response


# TODO: should we destroy all sessions?
def logout():
    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname', 'auth_user_access_token']:
        try:
            del session.data[key]
        except KeyError:
            pass
    Session.remove(Q('_id', 'eq', session._id))
    return True


def register_unconfirmed(username, password, fullname, campaign=None):
    user = get_user(email=username)
    if not user:
        user = User.create_unconfirmed(
            username=username,
            password=password,
            fullname=fullname,
            campaign=campaign,
        )
        user.save()
        signals.unconfirmed_user_created.send(user)

    elif not user.is_registered:  # User is in db but not registered
        user.add_unconfirmed_email(username)
        user.set_password(password)
        user.fullname = fullname
        user.update_guessed_names()
        user.save()
    else:
        raise DuplicateEmailError('User {0!r} already exists'.format(username))
    return user


def get_or_create_user(fullname, address, is_spam=False):
    """Get or create user by email address.

    :param str fullname: User full name
    :param str address: User email address
    :param bool is_spam: User flagged as potential spam
    :return: Tuple of (user, created)
    """
    user = get_user(email=address)
    if user:
        return user, False
    else:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        user.verification_key = generate_verification_key()
        if is_spam:
            user.system_tags.append('is_spam')
        return user, True
