import Framework.Beaker as Session
import Framework.Mongo as Database
import Framework.Status as Status
import Framework.Flask as Web
import Framework.Bcrypt as Bcrypt
import Framework.Debug as Debug

import Helper

#import Site.Settings as Settings

from Model import *

from decorator import decorator
import datetime

def getCurrentUsername():
    return Session.get('auth_user_username')

def getCurrentUserId():
    return Session.get('auth_user_id')

def getCurrentUser():
    # tag: database
    uid = Session.get("auth_user_id")
    if uid:
        return User.load(uid)
    else:
        return None

def checkPassword(actualPassword, givenPassword):
    return Bcrypt.check_password_hash(actualPassword, givenPassword)

def getUser(id=None, username=None, password=None, verification_key=None):
    # tag: database
    query = {}
    if id:
        query['_id'] = id
    if username:
        username = username.strip().lower()
        query['username'] = username
    if password:
        password = password.strip()
        user = User.find(**query)
        if user and not checkPassword(user.password, password):
            return False
        else:
            return user
    if verification_key:
        query['verification_key'] = verification_key
    return User.find(**query)

def login(username, password):
    username = username.strip().lower()
    password = password.strip()

    if username and password:
        user = getUser(username=username, password=password)
        if user:
            if not user.is_registered:
                return 2
            elif not user.is_claimed:
                return False
            else:
                Session.set([
                    ('auth_user_username', user.username), 
                    ('auth_user_id', user.id),
                    ('auth_user_fullname', user.fullname)
                ])
                return True
    return False

def logout():
    Session.unset(['auth_user_username', 'auth_user_id', 'auth_user_fullname'])
    return True

def addUnclaimedUser(email, fullname):
    email = email.strip().lower()
    fullname = fullname.strip()

    user = getUser(username=email)
    if user:
        return user
    else:
        user_based_on_email = User.find(emails=email)
        if user_based_on_email:
            return user_based_on_email
        newUser = User(
            fullname=fullname,
            emails = [email],
        )
        newUser.optimistic_insert()
        newUser.save()
        return newUser        

def hash_password(password):
    return Bcrypt.generate_password_hash(password.strip())

def register(username, password, fullname=None):
    username = username.strip().lower()
    fullname = fullname.strip()

    if not getUser(username=username):
        newUser = User(
            username=username,
            password=hash_password(password),
            fullname=fullname,
            is_registered=True,
            is_claimed=True,
            verification_key=Helper.randomString(15),
            date_registered=datetime.datetime.utcnow()
        )
        newUser.optimistic_insert()
        newUser.emails.append(username.strip())
        newUser.save()
        newUser.generate_keywords()
        return newUser
    else:
        return False

###############################################################################

def mustBeLoggedIn(fn):
    def wrapped(func, *args, **kwargs):
        user = getCurrentUser()
        if user:
            kwargs['user'] = user
            return func(*args, **kwargs)
        else:
            Status.pushStatusMessage('You are not logged in')
            return Web.redirect('/account')
    return decorator(wrapped, fn)