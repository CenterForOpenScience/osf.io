from furl import furl
import re

from flask import request

from framework.auth.core import get_user
from framework.auth.signals import user_confirmed
from framework.celery_tasks import app
from framework.celery_tasks.handlers import queued_task

from website import settings
from website.notifications.utils import to_subscription_key

from website.mailing_list.model import MailingListEventLog
from website.project.signals import contributor_added

ANGLE_BRACKETS_REGEX = re.compile(r'<(.*?)>')


###############################################################################
# List Management Functions
###############################################################################

# TODO

def get_list(node):
    """ Returns information about the mailing list from Mailgun
    :param Node node: The node in question
    :returns: info, members: Two dictionaries about list and members
    """
    pass

def enable_list(node, unsubs):
    """ Creates a new mailing list on Mailgun with all emails and subscriptions
    :param Node node: The node in question
    """
    pass

def disable_list(node):
    """ Prevents further use of this list by users
    :param Node node: The node in question
    """
    pass

def update_title(node):
    """ Updates the title of a mailing list to match the list's project
    :param Node node: The node in question
    """
    pass

def update_single_user_in_list(node, user, enabled, old_email=None):
    """ Adds/updates single member of a mailing list on Mailgun
    :param Node node: The id of the node in question
    :param User user: User to update
    :param bool enabled: Enable or disable user?
    :param str old_email: Previous email of this user in list
    """
    pass

def remove_user_from_list(node, user):
    """ Removes single member of a mailing list on Mailgun
    :param Node node: The id of the node in question
    :param User user: User to remove
    """

def update_multiple_users_in_list(node, users):
    """ Adds/updates members of a mailing list on Mailgun
    :param Node node: The id of the node in question
    :param list users: List of Users to add/enable/update
    """
    pass

def check_node_list_synchronized(node, recover=False):
    """ Checks to see if the list is synchronized with internal representation
    :param Node node: The node to check
    :param bool recover: Should attempt to synchronize?
    :return bool: is synchronized?
    """
    pass

def get_recipients_remote(node):
    pass

###############################################################################
# Celery Queued tasks
###############################################################################

# TODO queue above tasks

@queued_task
@app.task
def send_message(node, message):
    """ Sends a message from the node through the given mailing list
    :param Node node: The id of the node in question
    :param dict message: Contains subject and text of the email to be sent
    """

###############################################################################
# Signalled Functions
###############################################################################

@contributor_added.connect
def subscribe_contributor_to_mailing_list(node, contributor, auth=None):
    if node.mailing_enabled and contributor.is_active:
        subscription = node.get_or_create_mailing_list_subscription()
        subscription.add_user_to_subscription(contributor, 'email_transactional', save=True)
        subscription.save()
        # TODO queue task

@user_confirmed.connect
def resubscribe_on_confirm(user):
    for node in user.contributed:
        subscribe_contributor_to_mailing_list(node, user)
    pass

###############################################################################
# Mailing List Helper Functions
###############################################################################

def address(node_id):
    return '{}@{}'.format(node_id, furl(settings.DOMAIN).host)

def find_email(long_email):
    # allow for both "{email}" syntax and "{name} <{email}>" syntax
    if '<' in long_email:
        email_match = ANGLE_BRACKETS_REGEX.search(long_email)
        if email_match:
            return email_match.groups()[0].lower().strip()
    elif '@' in long_email:
        return long_email.lower().strip()
    return None

def log_message(**kwargs):
    """ Acquires and logs messages sent through Mailgun"""
    from website.models import Node  # avoid circular imports
    message = request.form
    target = find_email(message['To'])
    node = Node.load(re.search(r'[a-z0-9]*@', target).group(0)[:-1])

    sender_email = find_email(message['From'])
    sender = get_user(email=sender_email)

    # Create a log of this mailing event
    MailingListEventLog(
        email_content=message,
        destination_node=node,
        sending_user=sender,
    ).save()

def get_recipients(node, sender=None):
    if node.mailing_enabled:
        from website.models import NotificationSubscription  # avoid circular import
        subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
        return [u for u in subscription.email_transactional if not u == sender]
    return []

def get_unsubscribes(node):
    # Non-subscribed users not guaranteed to be in subscription.none
    # Safer to calculate it
    if node.mailing_enabled:
        recipients = get_recipients(node)
        return [u for u in node.contributors if u not in recipients]
    return []
