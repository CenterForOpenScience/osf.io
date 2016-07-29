import json
import re
import requests
from urllib2 import HTTPError

from mailmanclient import Client
from modularodm import Q

from framework.auth import User
from framework.auth.core import get_user
from framework.auth.signals import user_confirmed
from framework.celery_tasks import app
from framework.celery_tasks.handlers import queued_task
from framework.exceptions import HTTPError

from website import settings
from website.project.signals import contributor_added, contributor_removed, node_deleted
from website.notifications.utils import to_subscription_key

#from website.mailing_list.model import MailingListEventLog

###
# Initialize some resources/ ensure they exist.
#######

mailman_api_url = 'http://{}:{}/{}'.format(
    settings.MAILMAN_API_DOMAIN,
    settings.MAILMAN_API_PORT,
    settings.MAILMAN_API_VERSION
    )

mc = Client(
    mailman_api_url,
    settings.MAILMAN_API_USERNAME,
    settings.MAILMAN_API_PASSWORD
    )

# Ensure the domain that the mailing lists we will be creating should be on exists.
# If it does not, the create it.
if settings.OSF_MAILING_LIST_DOMAIN in map(lambda x: x.mail_host, mc.domains):    
    mail_domain = mc.get_domain(settings.OSF_MAILING_LIST_DOMAIN)
else:
    mail_domain = mc.create_domain(settings.OSF_MAILING_LIST_DOMAIN)


###############################################################################
# Define some tools to manipulate the mailman client
###############################################################################

class MailingListError():
    pass


def with_list_proxy(fn):
    @app.task(name=fn.__name__)
    def get_proxy(*args, **kwargs):
        try:
            kwargs['list_proxy'] = mc.get_list('{}@{}'.format(kwargs['list_mailbox'], settings.OSF_MAILING_LIST_DOMAIN))
        except:
            kwargs['list_proxy'] = mail_domain.create_list(kwargs['list_mailbox'])
        fn(*args, **kwargs)
    def _fn(*args, **kwargs):
        if kwargs.get('contributors'):
            kwargs['contributors'] = list(map(lambda contributor: ensure_user_as_id(contributor), kwargs['contributors']))
        if kwargs.get('list_proxy'):
            fn(*args, **kwargs)
        else:
            get_proxy.apply_async(args=args, kwargs=kwargs)
    return _fn

# If we call this, we need a mailing list. If it doesn't exist yet, we should 
# create it. If it does exist, we should ensure it is up to date.
# This calls out to another server, so we should not be block.
@with_list_proxy 
def upsert_list(list_title=None, list_description=None, list_proxy=None, list_mailbox=None, contributors=None, public=False):
    stt = list_proxy.settings
    stt[u'display_name'] = list_title
    stt[u'description'] = list_description
    stt[u'archive_policy'] = 'public' if public else 'private'
    stt.save()
    contributors and add_contributors(list_mailbox=list_mailbox, contributors=contributors)

def ensure_user_as_id(contributor):
    if not isinstance(contributor, unicode):
        return contributor._id
    else:
        return contributor

@user_confirmed.connect
def subscribe_on_confirm(user):
    for node in user.contributed:
        subscribe_contributor_to_mailing_list(node, user)

# Adds all of the emails associated with a user to a given mailing list.
# This calls out to another server, so we should not block.
# TODO: accept both user objects and guids as args.
@with_list_proxy
def add_contributor(list_mailbox=None, list_proxy=None, contributor=None):
    def not_subbed(email):
        try:
            list_proxy.get_member(email)
            return False
        except:
            return True
    contributor = User.load(contributor)
    to_sub = list(filter(not_subbed, contributor.emails))
    map(lambda email: list_proxy.subscribe(
        email,
        contributor.fullname,
        pre_verified = True,
        pre_confirmed = True
        ), to_sub)

def add_contributors(list_mailbox=None, contributors=None):
    contributors = list(map(lambda contributor: ensure_user_as_id(contributor), contributors))
    map(lambda contributor: add_contributor(list_mailbox=list_mailbox, contributor=contributor), contributors)

@contributor_added.connect
def contributor_added_handler(node, contributor, auth=None, throttle=None):
    add_contributor(list_mailbox=node._id, contributor=contributor._id)

@with_list_proxy
def remove_contributor(list_proxy, contributor):
    def subbed(email):
        try:
            list_proxy.get_member(email)
            return True
        except:
            return False
    to_unsub = list(filter(subbed, contributor.emails))
    map(lambda email: list_proxy.unsubscribe(email))

def remove_contributors(list_proxy, contributors):
    map(lambda contributor: remove_contributor(list_proxy=list_proxy, contributor=contributor), contributors)

@contributor_removed.connect
def contributor_removed_handler(node, contributor, auth=None, throttle=None):
    remove_contributor(node._id, contributor)

def update_single_user_in_list(node_id, user_id, email=None, enabled=True, old_email=None):
    add_contributor(list_mailbox=node_id, list_proxy=None, contributor=user_id)


###############################################################################
# Celery Queued tasks
###############################################################################

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_create_list(*args, **kwargs):
    create_list(*args, **kwargs)

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_delete_list(*args, **kwargs):
    delete_list(*args, **kwargs)

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_update_title(*args, **kwargs):
    update_title(*args, **kwargs)

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_update_single_user_in_list(*args, **kwargs):
    update_single_user_in_list(*args, **kwargs)

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_remove_user_from_list(*args, **kwargs):
    remove_user_from_list(*args, **kwargs)

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_update_multiple_users_in_list(*args, **kwargs):
    update_multiple_users_in_list(*args, **kwargs)

@queued_task
@app.task(max_retries=3, default_retry_delay=3 * 60)  # Retry after 3 minutes
def celery_full_update(*args, **kwargs):
    full_update(*args, **kwargs)

def log_message(target, sender_email, message):
    """ Acquires and logs messages sent through Mailgun"""
    from website.models import Node  # avoid circular imports

    if target:
        node = Node.load(re.search(r'[a-z0-9]*@', target).group(0)[:-1])
    else:
        node = None

    sender = get_user(email=sender_email)

    # Create a log of this mailing event
    MailingListEventLog(
        email_content=message,
        destination_node=node,
        sending_user=sender,
    ).save()

def get_recipients(node):
    # Subscription options for mailing lists are 'transactional' and 'none'
    if node.mailing_enabled:
        from website.models import NotificationSubscription  # avoid circular import
        subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
        return subscription.email_transactional
    return []

def get_unsubscribes(node):
    # Non-subscribed users not guaranteed to be in subscription.none
    # Safer to calculate it
    if node.mailing_enabled:
        recipients = get_recipients(node)
        return [u for u in node.contributors if u not in recipients]
    return []
