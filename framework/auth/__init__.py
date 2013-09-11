from framework import session
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

def get_current_username():
    return session.get('auth_user_username', None)

def get_current_user_id():
    return session.get('auth_user_id', None)

def get_current_user():
    # tag: database
    uid = session.get("auth_user_id", None)
    if uid:
        return User.load(uid)
    else:
        return None

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
                response = web.redirect('/')
                print response
                key, cookie = web.create_key_and_cookie()
                response.set_cookie(cookie[0], value=cookie[1])
                web.g.session_id = key
                session.update({
                    'auth_user_username': user.username,
                    'auth_user_id': user._primary_key,
                    'auth_user_fullname': user.fullname,
                })
                print session
                return response
    return False

def logout():
    for i in ['auth_user_username', 'auth_user_id', 'auth_user_fullname']:
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
            status.push_status_message('You are not logged in')
            return web.redirect('/account')
    return decorator(wrapped, fn)