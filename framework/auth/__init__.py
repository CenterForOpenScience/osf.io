from framework import session, create_session, HTTPError
import framework.mongo as Database
import framework.status as status
import framework.flask as web
import framework.bcrypt as bcrypt

from modularodm.query.querydialect import DefaultQueryDialect as Q

import helper

#import website.settings as settings

from model import User

from decorator import decorator
import datetime

import httplib as http

def get_current_username():
    return session.get('auth_user_username', None)

def get_current_user_id():
    return session.get('auth_user_id', None)

def get_current_user():
    uid = session.get("auth_user_id", None)
    return User.load(uid)
    # if uid:
    #     return User.load(uid)
    # else:
    #     return None

# def get_current_node():
#     from website.models import Node
#     nid = session.get('auth_node_id')
#     if nid:
#         return Node.load(nid)

def get_api_key():
    # Hack: Avoid circular import
    from website.project.model import ApiKey
    api_key = session.get('auth_api_key')
    return ApiKey.load(api_key)

def get_user_or_node():
    uid = get_current_user()
    if uid:
        return uid
    return get_current_node()

def check_password(actualPassword, givenPassword):
    return bcrypt.check_password_hash(actualPassword, givenPassword)

def get_user(id=None, username=None, password=None, verification_key=None):
    # tag: database
    query = []
    if id:
        query.append(Q('_id', 'eq', id))
    if username:
        username = username.strip().lower()
        query.append(Q('username', 'eq', username))
    if password:
        password = password.strip()
        try:
            user = User.find_one(*query)
        except:
            user = None
        if user and not check_password(user.password, password):
            return False
        return user
    if verification_key:
        query.append(Q('verification_key', 'eq', verification_key))
    try:
        return User.find_one(*query)
    except:
        return None

def login(username, password):
    username = username.strip().lower()
    password = password.strip()

    if username and password:
        user = get_user(
            username=username,
            password=password
        )
        if user:
            if not user.is_registered:
                return 2
            elif not user.is_claimed:
                return False
            else:
                response = web.redirect('/dashboard/')
                response = create_session(response, data={
                    'auth_user_username': user.username,
                    'auth_user_id': user._primary_key,
                    'auth_user_fullname': user.fullname,
                })
                return response
    return False

def logout():
    for i in ['auth_user_username', 'auth_user_id', 'auth_user_fullname']:
        # todo leave username so login page can persist probable id
        del session[i]
    return True

def add_unclaimed_user(email, fullname):
    email = email.strip().lower()
    fullname = fullname.strip()

    user = get_user(username=email)
    if user:
        return user
    else:
        user_based_on_email = User.find_one(
            Q('emails', 'eq', email)
        )
        if user_based_on_email:
            return user_based_on_email
        newUser = User(
            fullname = fullname,
            emails = [email],
        )
        newUser._optimistic_insert()
        newUser.save()
        return newUser

def hash_password(password):
    return bcrypt.generate_password_hash(password.strip())


class DuplicateEmailError(BaseException):
    pass


def register(username, password, fullname=None):
    username = username.strip().lower()
    fullname = fullname.strip()

    if not get_user(username=username):
        newUser = User(
            username=username,
            password=hash_password(password),
            fullname=fullname,
            is_registered=True,
            is_claimed=True,
            verification_key=helper.random_string(15),
            date_registered=datetime.datetime.utcnow()
        )
        # newUser._optimistic_insert()
        newUser.emails.append(username.strip())
        newUser.save()
        newUser.generate_keywords()
        return newUser
    else:
        raise DuplicateEmailError

###############################################################################

def must_be_logged_in(fn):
    def wrapped(func, *args, **kwargs):
        user = get_current_user()
        if user:
            kwargs['user'] = user
            return func(*args, **kwargs)
        else:
            raise HTTPError(http.UNAUTHORIZED)
            # status.push_status_message('You are not logged in')
            # return web.redirect('/account')
    return decorator(wrapped, fn)

def must_have_session_auth(fn):

    def wrapped(func, *args, **kwargs):

        kwargs['user'] = get_current_user()
        kwargs['api_key'] = get_api_key()
        if kwargs['user'] or kwargs['api_key']:
            return func(*args, **kwargs)
        # kwargs['api_node'] = get_current_node()

        # Get user from session
        # user = get_current_user()
        # if kwargs['user']:
            # kwargs['user'] = user
            # return func(*args, **kwargs)

        # Get node from session
        # node = get_current_node()
        # if node:
        # if kwargs['api_key']:
            # kwargs['api_node'] = node
            # return func(*args, **kwargs)

        print(kwargs)
        # No session authentication found
        raise HTTPError(http.UNAUTHORIZED)

    return decorator(wrapped, fn)
