# -*- coding: utf-8 -*-
import logging

from mako.template import Template
from framework import session, create_session
from framework import goback
from framework import status
from framework.auth.utils import parse_name
import framework.flask as web
import framework.bcrypt as bcrypt
from framework.email.tasks import send_email
from modularodm.query.querydialect import DefaultQueryDialect as Q

import website
from website import security
from model import User

import datetime


def get_current_username():
    return session.data.get('auth_user_username')


def get_current_user_id():
    return session.data.get('auth_user_id')


def get_current_user():
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return User.load(uid)


def get_display_name(username):
    """Return the username to display in the navbar. Shortens long usernames."""
    if len(username) > 22:
        return '%s...%s' % (username[:9], username[-10:])
    return username


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
            logging.debug("Incorrect password attempt.")
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
    except Exception as err:  # TODO: Should catch a specific type of exception
        logging.error(err)
        return None


def login(username, password):
    username = username.strip().lower()
    password = password.strip()
    logging.info("Attempting to log in {0}".format(username))

    if username and password:
        user = get_user(
            username=username,
            password=password
        )
        if user:
            if not user.is_registered:
                logging.debug("User is not registered")
                return 2
            elif not user.is_claimed:
                logging.debug("User is not claimed")
                return False
            else:
                is_first_login = user.date_last_login is None
                user.date_last_login = datetime.datetime.utcnow()
                user.save()
                if not is_first_login:
                    response = goback()
                else:
                    # Direct user to settings page if first login; need to
                    # verify imputed names
                    status.push_status_message('Welcome to the OSF! Please update the '
                                        'following settings. If you need assistance '
                                        'in getting started, please visit the '
                                        '<a href="/getting-started/">Getting Started</a> '
                                        'page.')
                    response = web.redirect('/settings/')
                data = session.data if session._get_current_object() else {}
                data.update({
                    'auth_user_username': user.username,
                    'auth_user_id': user._primary_key,
                    'auth_user_fullname': user.fullname,
                })
                response = create_session(response, data=data)
                return response
    return False

def logout():
    for key in ['auth_user_username', 'auth_user_id', 'auth_user_fullname']:
        # todo leave username so login page can persist probable id
        del session.data[key]
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

# TODO: should inherit from framework.excpeptions.FrameworkError
class DuplicateEmailError(BaseException):
    pass


# TODO: Use mails.py interface
WELCOME_EMAIL_SUBJECT = 'Welcome to the Open Science Framework'
WELCOME_EMAIL_TEMPLATE = Template('''
Hello ${fullname},

Welcome to the Open Science Framework! To learn more about the OSF, check out our Getting Started guide [ https://osf.io/getting-started/ ] and our frequently asked questions [ https://osf.io/faq/ ].

If you have any questions or comments about the OSF, please let us know at [ contact@osf.io ]!

Follow OSF at @OSFramework on Twitter [ https://twitter.com/OSFramework ]
Like us on Facebook [ https://www.facebook.com/OpenScienceFramework ]

From the Open Science Framework Robot
''')


def send_welcome_email(user):
    send_email.delay(
        from_addr=website.settings.FROM_EMAIL,
        to_addr=user.username,
        subject=WELCOME_EMAIL_SUBJECT,
        message=WELCOME_EMAIL_TEMPLATE.render(
            fullname=user.fullname,
        ),
        mimetype='plain',
    )


def register(username, password, fullname, send_welcome=True):
    username = username.strip().lower()
    fullname = fullname.strip()

    # TODO: This validation should occur at the database level, not the view
    if not get_user(username=username):
        parsed = parse_name(fullname)
        # TODO: add User.create_registered() class method
        user = User(
            username=username,
            fullname=fullname,
            is_registered=True,
            is_claimed=True,
            verification_key=security.random_string(15),
            date_registered=datetime.datetime.utcnow(),
            **parsed
        )
        # Set the password
        user.set_password(password.strip())
        user.emails.append(username.strip())
        user.save()
        if send_welcome:
            send_welcome_email(user)
        return user
    else:
        raise DuplicateEmailError
