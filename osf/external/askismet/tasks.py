from framework.celery_tasks import app as celery_app

from osf.external.askismet.client import AkismetClient
from website import settings


@celery_app.task(
    soft_time_limit=settings.SPAM_SUBMIT_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.SPAM_SUBMIT_TASK_HARD_TIME_LIMIT,
)
def submit_spam(guid):
    from osf.models import Guid
    resource = Guid.load(guid).referent

    client = AkismetClient()

    client.submit_spam(
        user_ip=resource.spam_data['headers']['Remote-Addr'],
        user_agent=resource.spam_data['headers'].get('User-Agent'),
        referrer=resource.spam_data['headers'].get('Referer'),
        comment_content=resource.spam_data['content'],
        comment_author=resource.spam_data['author'],
        comment_author_email=resource.spam_data['author_email'],
    )


@celery_app.task(
    soft_time_limit=settings.SPAM_SUBMIT_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.SPAM_SUBMIT_TASK_HARD_TIME_LIMIT,
)
def submit_ham(guid):
    from osf.models import Guid
    resource = Guid.load(guid).referent

    client = AkismetClient()

    client.submit_ham(
        user_ip=resource.spam_data['headers']['Remote-Addr'],
        user_agent=resource.spam_data['headers'].get('User-Agent'),
        referrer=resource.spam_data['headers'].get('Referer'),
        comment_content=resource.spam_data['content'],
        comment_author=resource.spam_data['author'],
        comment_author_email=resource.spam_data['author_email'],
    )
