# -*- coding: utf-8 -*-
import uuid

from django.utils import timezone

from framework import bcrypt
from framework.auth import signals
from framework.auth.core import User, Auth
from framework.auth.core import get_user, generate_verification_key
from framework.auth.exceptions import DuplicateEmailError
from framework.sessions import session, create_session
from framework.sessions.utils import remove_session


__all__ = [
    'get_display_name',
    'Auth',
    'User',
    'get_user',
    'check_password',
    'authenticate',
    'external_first_login_authenticate',
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
    user.date_last_login = timezone.now()
    user.clean_email_verifications()
    user.update_affiliated_institutions_by_email_domain()
    user.save()
    response = create_session(response, data=data)
    return response


def external_first_login_authenticate(user, response):
    """
    Create a special unauthenticated session for user login through external identity provider for the first time.

    :param user: the user with external credential
    :param response: the response to return
    :return: the response
    """

    data = session.data if session._get_current_object() else {}
    data.update({
        'auth_user_external_id_provider': user['external_id_provider'],
        'auth_user_external_id': user['external_id'],
        'auth_user_fullname': user['fullname'],
        'auth_user_access_token': user['access_token'],
        'auth_user_external_first_login': True,
        'service_url': user['service_url'],
    })
    response = create_session(response, data=data)
    return response


def logout():
    """Clear users' session(s) and log them out of OSF."""

    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname', 'auth_user_access_token']:
        try:
            del session.data[key]
        except KeyError:
            pass
    remove_session(session)
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


def get_or_create_user(fullname, address, reset_password=True, is_spam=False):
    """
    Get or create user by fullname and email address.

    :param str fullname: user full name
    :param str address: user email address
    :param boolean reset_password: ask user to reset their password
    :param bool is_spam: user flagged as potential spam
    :return: tuple of (user, created)
    """
    user = get_user(email=address)
    if user:
        return user, False
    else:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        if password:
            user.verification_key_v2 = generate_verification_key(verification_type='password')
        if is_spam:
            user.save()  # need to save in order to add a tag
            user.add_system_tag('is_spam')
        return user, True
