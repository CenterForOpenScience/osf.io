import mailchimp
from website import settings
from framework.tasks import app


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
def subscribe(list_name, username):
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    m.lists.subscribe(id=list_id, email={'email': username}, double_optin=False, update_existing=True)


@app.task
def unsubscribe(list_name, username):
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    m.lists.unsubscribe(id=list_id, email={'email': username})


subscribe_mailchimp = (
    subscribe.delay
    if settings.USE_CELERY
    else subscribe)

unsubscribe_mailchimp = (
    unsubscribe.delay
    if settings.USE_CELERY
    else unsubscribe
)