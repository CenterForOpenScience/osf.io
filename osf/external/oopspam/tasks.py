from framework import sentry
from framework.celery_tasks import app as celery_app

from osf.external.oopspam.client import OOPSpamClient
from osf.external.oopspam.exceptions import OOPSpamClientError


@celery_app.task()
def check_resource_with_oopspam(guid, content, author, author_email, request_kwargs):
    from osf.models import Guid
    resource = Guid.load(guid).referent
    client = OOPSpamClient()

    try:
        is_spam, oopspam_details = client.check_content(
            user_ip=request_kwargs['remote_addr'],
            content=content
        )
    except OOPSpamClientError:
        sentry.log_exception()
        return

    resource.spam_data['headers'] = request_kwargs
    resource.spam_data['content'] = content
    resource.spam_data['author'] = author
    resource.spam_data['author_email'] = author_email
    resource.spam_data['oopspam_data'] = oopspam_details
    if is_spam:
        resource.flag_spam()
        if not resource.spam_data.get('who_flagged'):
            resource.spam_data['who_flagged'] = 'oopspam'
        elif resource.spam_data['who_flagged'] == 'akismet':
            resource.spam_data['who_flagged'] = 'both'

    resource.save()

    return is_spam
