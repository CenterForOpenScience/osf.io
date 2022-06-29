# -*- coding: utf-8 -*-
import uuid

from django.utils import timezone

from framework import bcrypt
from framework.auth import signals
from framework.auth.core import Auth
from framework.auth.core import get_user, generate_verification_key
from framework.auth.exceptions import DuplicateEmailError
from framework.auth.tasks import update_user_from_activity
from framework.auth.utils import LogLevel, print_cas_log
from framework.celery_tasks.handlers import enqueue_task
from framework.sessions import session, create_session
from framework.sessions.utils import remove_session


__all__ = [
    'Auth',
    'get_user',
    'check_password',
    'authenticate',
    'external_first_login_authenticate',
    'logout',
    'register_unconfirmed',
]


# check_password(actual_pw_hash, given_password) -> Boolean
check_password = bcrypt.check_password_hash


def authenticate(user, access_token, response, user_updates=None):
    data = session.data if session._get_current_object() else {}
    data.update({
        'auth_user_username': user.username,
        'auth_user_id': user._primary_key,
        'auth_user_fullname': user.fullname,
        'auth_user_access_token': access_token,
    })
    print_cas_log(f'Finalizing authentication - data updated: user=[{user._id}]', LogLevel.INFO)
    enqueue_task(update_user_from_activity.s(user._id, timezone.now().timestamp(), cas_login=True, updates=user_updates))
    print_cas_log(f'Finalizing authentication - user update queued: user=[{user._id}]', LogLevel.INFO)
    response = create_session(response, data=data)
    print_cas_log(f'Finalizing authentication - session created: user=[{user._id}]', LogLevel.INFO)
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
    user_identity = '{}#{}'.format(user['external_id_provider'], user['external_id'])
    print_cas_log(
        f'Finalizing first-time login from external IdP - data updated: user=[{user_identity}]',
        LogLevel.INFO,
    )
    response = create_session(response, data=data)
    print_cas_log(
        f'Finalizing first-time login from external IdP - anonymous session created: user=[{user_identity}]',
        LogLevel.INFO,
    )
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


def register_unconfirmed(username, password, fullname, campaign=None, accepted_terms_of_service=None):
    from osf.models import OSFUser
    user = get_user(email=username)
    if not user:
        user = OSFUser.create_unconfirmed(
            username=username,
            password=password,
            fullname=fullname,
            campaign=campaign,
            accepted_terms_of_service=accepted_terms_of_service
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
        raise DuplicateEmailError('OSFUser {0!r} already exists'.format(username))
    return user


def get_or_create_institutional_user(fullname, sso_email, eppn=None):
    """
    Get or create an institutional user by fullname, email address and eppn (optional). Returns a tuple of three
    objects ``(user, is_created, email_to_add)``: the user to authenticate, whether the user is newly created or
    not, and an extra email to add to the user later (after the user passes status check).

    :param str fullname: user's full name
    :param str sso_email: user's email, which comes from the email attribute during SSO
    :param str eppn: user's eppn, which comes from the identity attribute during SSO
    """

    from osf.models import OSFUser
    email_user = get_user(email=sso_email)
    # If eppn is provided by CAS, check if an account already exists using eppn as email.
    if eppn:
        eppn_user = get_user(email=eppn)
        if eppn_user:
            if not email_user:
                # CASE 1/5: If the email doesn't belong to any user, return both the eppn_user and the sso_email.
                return eppn_user, False, sso_email
            if email_user == eppn_user:
                # CASE 2/5: Return the user only since sso_email already belongs to the same user
                return email_user, False, None
            # CASE 3/5: When eppn and sso_email point to different users, the sso_email takes priority
            return email_user, False, None
    # If eppn is not provided, use email_user if found.
    if email_user:
        # CASE 4/5: user only found via email
        return email_user, False, None
    # CASE 5/5: If no user is found, create a confirmed user and return it.
    # Institution users are created as confirmed with a strong and random password. Users don't need the password
    # since they sign in via institution SSO. They can reset their password to enable email/password login.
    user = OSFUser.create_confirmed(sso_email, str(uuid.uuid4()), fullname)
    return user, True, None


def get_or_create_user(fullname, address, reset_password=True, is_spam=False):
    """
    Get or create user by fullname and email address.

    :param str fullname: user full name
    :param str address: user email address
    :param boolean reset_password: ask user to reset their password
    :param bool is_spam: user flagged as potential spam
    :return: tuple of (user, created)
    """
    from osf.models import OSFUser
    user = get_user(email=address)
    if user:
        return user, False
    else:
        password = str(uuid.uuid4())
        user = OSFUser.create_confirmed(address, password, fullname)
        if reset_password:
            user.verification_key_v2 = generate_verification_key(verification_type='password')
        if is_spam:
            user.save()  # need to save in order to add a tag
            user.add_system_tag('is_spam')
        return user, True
