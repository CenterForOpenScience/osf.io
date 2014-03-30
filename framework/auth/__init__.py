# -*- coding: utf-8 -*-
import logging

from framework import session, create_session
from framework import goback
import framework.bcrypt as bcrypt
from modularodm.query.querydialect import DefaultQueryDialect as Q
from framework.auth.exceptions import (DuplicateEmailError, LoginNotAllowedError,
                                        PasswordIncorrectError)

from model import User


logger = logging.getLogger(__name__)

def get_current_username():
    return session.data.get('auth_user_username')


def get_current_user_id():
    return session.data.get('auth_user_id')


def get_current_user():
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return User.load(uid)


def get_display_name(username):
    """Return the username to display in the navbar. Shortens long usernames."""
    if len(username) > 40:
        return '%s...%s' % (username[:15], username[-10:])
    return username

# TODO(sloria): This belongs in website.project
def get_current_node():
    from website.models import Node
    nid = session.data.get('auth_node_id')
    if nid:
        return Node.load(nid)


def get_api_key():
    # Hack: Avoid circular import
    from website.project.model import ApiKey
    api_key = session.data.get('auth_api_key')
    return ApiKey.load(api_key)


# check_password(actual_pw_hash, given_password) -> Boolean
check_password = bcrypt.check_password_hash

# TODO: This should be a class method of User
def get_user(id=None, username=None, password=None, verification_key=None):
    # tag: database
    query_list = []
    if id:
        query_list.append(Q('_id', 'eq', id))
    if username:
        username = username.strip().lower()
        query_list.append(Q('username', 'eq', username))
    if password:
        password = password.strip()
        try:
            query = query_list[0]
            for query_part in query_list[1:]:
                query = query & query_part
            user = User.find_one(query)
        except Exception as err:
            logging.error(err)
            user = None
        if user and not user.check_password(password):
            return False
        return user
    if verification_key:
        query_list.append(Q('verification_key', 'eq', verification_key))
    try:
        query = query_list[0]
        for query_part in query_list[1:]:
            query = query & query_part
        user = User.find_one(query)
        return user
    except Exception as err:
        logging.error(err)
        return None


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
