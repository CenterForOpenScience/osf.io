from framework.celery_tasks import app as celery_app

from osf.external.askismet.client import AkismetClient


@celery_app.task()
def submit_spam(guid):
    from osf.models import Guid

    resource = Guid.load(guid).referent

    client = AkismetClient()

    client.submit_spam(
        user_ip=resource.spam_data["headers"]["Remote-Addr"],
        user_agent=resource.spam_data["headers"].get("User-Agent"),
        referrer=resource.spam_data["headers"].get("Referer"),
        comment_content=resource.spam_data["content"],
        comment_author=resource.spam_data["author"],
        comment_author_email=resource.spam_data["author_email"],
    )


@celery_app.task()
def submit_ham(guid):
    from osf.models import Guid

    resource = Guid.load(guid).referent

    client = AkismetClient()

    client.submit_ham(
        user_ip=resource.spam_data["headers"]["Remote-Addr"],
        user_agent=resource.spam_data["headers"].get("User-Agent"),
        referrer=resource.spam_data["headers"].get("Referer"),
        comment_content=resource.spam_data["content"],
        comment_author=resource.spam_data["author"],
        comment_author_email=resource.spam_data["author_email"],
    )
