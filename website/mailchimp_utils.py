# -*- coding: utf-8 -*-

import mailchimp

from framework import sentry
from framework.celery_tasks import app
from framework.auth.core import User
from framework.celery_tasks.handlers import queued_task
from framework.auth.signals import user_confirmed

from framework.transactions.context import transaction

from website import settings


def get_mailchimp_api():
    if not settings.MAILCHIMP_API_KEY:
        raise mailchimp.InvalidApiKeyError(
            "An API key is required to connect to Mailchimp."
        )
    return mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)


def get_list_id_from_name(list_name):
    m = get_mailchimp_api()
    mailing_list = m.lists.list(filters={'list_name': list_name})
    return mailing_list['data'][0]['id']


def get_list_name_from_id(list_id):
    m = get_mailchimp_api()
    mailing_list = m.lists.list(filters={'list_id': list_id})
    return mailing_list['data'][0]['name']


@queued_task
@app.task
@transaction()
def subscribe_mailchimp(list_name, user_id):
    user = User.load(user_id)
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)

    if user.mailchimp_mailing_lists is None:
        user.mailchimp_mailing_lists = {}

    try:
        m.lists.subscribe(
            id=list_id,
            email={'email': user.username},
            merge_vars={
                'fname': user.given_name,
                'lname': user.family_name,
            },
            double_optin=False,
            update_existing=True,
        )

    except mailchimp.ValidationError as error:
        sentry.log_exception()
        sentry.log_message(error.message)
        user.mailchimp_mailing_lists[list_name] = False
    else:
        user.mailchimp_mailing_lists[list_name] = True
    finally:
        user.save()


def unsubscribe_mailchimp(list_name, user_id, username=None, send_goodbye=True):
    """Unsubscribe a user from a mailchimp mailing list given its name.

    :param str list_name: mailchimp mailing list name
    :param str user_id: current user's id
    :param str username: current user's email (required for merged users)

    :raises: ListNotSubscribed if user not already subscribed
    """
    user = User.load(user_id)
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    m.lists.unsubscribe(id=list_id, email={'email': username or user.username}, send_goodbye=send_goodbye)

    # Update mailing_list user field
    if user.mailchimp_mailing_lists is None:
        user.mailchimp_mailing_lists = {}
        user.save()

    user.mailchimp_mailing_lists[list_name] = False
    user.save()

@queued_task
@app.task
@transaction()
def unsubscribe_mailchimp_async(list_name, user_id, username=None, send_goodbye=True):
    """ Same args as unsubscribe_mailchimp, used to have the task be run asynchronously
    """
    unsubscribe_mailchimp(list_name=list_name, user_id=user_id, username=username, send_goodbye=send_goodbye)

@user_confirmed.connect
def subscribe_on_confirm(user):
    # Subscribe user to general OSF mailing list upon account confirmation
    if settings.ENABLE_EMAIL_SUBSCRIPTIONS:
        subscribe_mailchimp(settings.MAILCHIMP_GENERAL_LIST, user._id)
