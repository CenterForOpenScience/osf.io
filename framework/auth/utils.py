from nameparser.parser import HumanName
import mailchimp
from website import settings
from framework.tasks import celery
from framework.exceptions import HTTPError
import httplib as http


def impute_names(name):
    human = HumanName(name)
    return {
        'given': human.first,
        'middle': human.middle,
        'family': human.last,
        'suffix': human.suffix,
    }


def impute_names_model(name):
    human = HumanName(name)
    return {
        'given_name': human.first,
        'middle_names': human.middle,
        'family_name': human.last,
        'suffix': human.suffix,
    }


def privacy_info_handle(info, anonymous, name=False):
    """hide user info from api if anonymous

    :param str info: info which suppose to return
    :param bool anonymous: anonymous or not
    :param bool name: if the info is a name,
    :return str: the handled info should be passed through api

    """
    if anonymous:
        return 'A user' if name else ''
    return info


def get_mailchimp_api():
    return mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)


def get_list_id_from_name(list_name):
    m = get_mailchimp_api()
    mailing_list = m.lists.list(filters={'list_name': list_name})
    return mailing_list['data'][0]['id']


def get_list_name_from_id(list_id):
    m = get_mailchimp_api()
    mailing_list = m.lists.list(filters={'list_id': list_id})
    return mailing_list['data'][0]['name']

@celery.task
def subscribe(list_name, username):
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    try:
        m.lists.subscribe(id=list_id, email={'email': username}, double_optin=False)
    except mailchimp.ListAlreadySubscribedError:
        pass

@celery.task
def unsubscribe(list_name, username):
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    try:
        m.lists.unsubscribe(id=list_id, email={'email': username})
    except mailchimp.ListNotSubscribedError:
        pass
