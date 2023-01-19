from framework.celery_tasks import app as celery_app

from osf.external.askismet.client import AkismetClient
from website import settings


@celery_app.task()
def check_resource_with_akismet(guid, content, author, author_email, request_kwargs):
    from osf.models import Guid
    resource = Guid.load(guid).referent

    client = AkismetClient(
        apikey=settings.AKISMET_APIKEY,
        website=settings.DOMAIN,
        verify=bool(settings.AKISMET_APIKEY)
    )

    is_spam, pro_tip = client.check_content(
        user_ip=request_kwargs.get('remote_addr'),
        user_agent=request_kwargs.get('user_agent'),
        referrer=request_kwargs.get('referer'),
        comment_content=content,
        comment_author=author,
        comment_author_email=author_email
    )

    resource.spam_pro_tip = pro_tip
    resource.spam_data['headers'] = {
        'Remote-Addr': request_kwargs.get('remote_addr'),
        'User-Agent': request_kwargs.get('user_agent'),
        'Referer': request_kwargs.get('referer'),
    }
    resource.spam_data['content'] = content
    resource.spam_data['author'] = author
    resource.spam_data['author_email'] = author_email

    if is_spam:
        resource.flag_spam()
        if not resource.spam_data.get('who_flagged'):
            resource.spam_data['who_flagged'] = 'akismet'
        elif resource.spam_data['who_flagged'] == 'oopspam':
            resource.spam_data['who_flagged'] = 'both'

    resource.save()

    return is_spam


@celery_app.task()
def submit_spam(guid):
    from osf.models import Guid
    resource = Guid.load(guid).referent

    client = AkismetClient(
        apikey=settings.AKISMET_APIKEY,
        website=settings.DOMAIN,
        verify=bool(settings.AKISMET_APIKEY)
    )

    client.submit_spam(
        user_ip=resource.spam_data['headers']['Remote-Addr'],
        user_agent=resource.spam_data['headers'].get('User-Agent'),
        referrer=resource.spam_data['headers'].get('Referer'),
        comment_content=resource.spam_data['content'],
        comment_author=resource.spam_data['author'],
        comment_author_email=resource.spam_data['author_email'],
    )


@celery_app.task()
def submit_ham(guid):
    from osf.models import Guid
    resource = Guid.load(guid).referent

    client = AkismetClient(
        apikey=settings.AKISMET_APIKEY,
        website=settings.DOMAIN,
        verify=bool(settings.AKISMET_APIKEY)
    )

    client.submit_ham(
        user_ip=resource.spam_data['headers']['Remote-Addr'],
        user_agent=resource.spam_data['headers'].get('User-Agent'),
        referrer=resource.spam_data['headers'].get('Referer'),
        comment_content=resource.spam_data['content'],
        comment_author=resource.spam_data['author'],
        comment_author_email=resource.spam_data['author_email'],
    )
