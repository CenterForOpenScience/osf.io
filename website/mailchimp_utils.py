import mailchimp
from website import settings
from framework.tasks import app
from framework.auth.core import User
from framework.auth.signals import user_confirmed


def get_mailchimp_api():
    if not settings.MAILCHIMP_API_KEY:
        raise RuntimeError("An API key is required to connect to Mailchimp.")
    return mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)


def get_list_id_from_name(list_name):
    m = get_mailchimp_api()
    mailing_list = m.lists.list(filters={'list_name': list_name})
    return mailing_list['data'][0]['id']


def get_list_name_from_id(list_id):
    m = get_mailchimp_api()
    mailing_list = m.lists.list(filters={'list_id': list_id})
    return mailing_list['data'][0]['name']

@app.task
def subscribe(list_name, user_id):
    user = User.load(user_id)
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    m.lists.subscribe(id=list_id, email={'email': user.username}, double_optin=False, update_existing=True)

    # Update mailing_list user field
    if user.mailing_lists is None:
        user.mailing_lists = {}
        user.save()

    user.mailing_lists[list_name] = True
    user.save()

@app.task
def unsubscribe(list_name, user_id):
    """ Unsubscribe a user from a mailchimp mailing list given its name.

        :param str list_name: mailchimp mailing list name
        :param str username: current user's email

        A ListNotSubscribed error will be raised if a user
        not subscribed to the list tries to unsubscribe again.
    """
    user = User.load(user_id)
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    m.lists.unsubscribe(id=list_id, email={'email': user.username})

    # Update mailing_list user field
    if user.mailing_lists is None:
        user.mailing_lists = {}
        user.save()

    user.mailing_lists[list_name] = False
    user.save()

@user_confirmed.connect
def subscribe_on_confirm(user):
    # Subscribe user to general OSF mailing list upon account confirmation
    if settings.ENABLE_EMAIL_SUBSCRIPTIONS:
        subscribe_mailchimp(settings.MAILCHIMP_GENERAL_LIST, user._id)

subscribe_mailchimp = (
    subscribe.delay
    if settings.USE_CELERY
    else subscribe)

unsubscribe_mailchimp = (
    unsubscribe.delay
    if settings.USE_CELERY
    else unsubscribe
)
