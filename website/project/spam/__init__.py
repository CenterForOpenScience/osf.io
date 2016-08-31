from framework.celery_tasks import app as celery_app

from website import settings
from website.util import akismet


@celery_app.task
def _check_for_spam(node_id, content, author_info, request_headers):
    client = akismet.AkismetClient(
        apikey=settings.AKISMET_APIKEY,
        website=settings.DOMAIN,
        verify=True
    )
    is_possible_spam, pro_tip = client.check_comment(
        user_ip=request_headers['Remote-Addr'],
        user_agent=request_headers['User-Agent'],
        referrer=request_headers.get('Referrer'),
        comment_content=content,
        comment_author=author_info['name'],
        comment_author_email=author_info['email']
    )
    if is_possible_spam:
        from website.project.model import Node
        node = Node.load(node_id)
        node.flag_spam(save=True)

def check_node_for_spam(document, creator, request_headers):
    content = """
    {}

    {}

    {}
    """.format(
        document['title'],
        document['description'],
        '\n'.join(document['wikis'].values())
    )

    _check_for_spam.delay(document['id'], content, {
        'email': creator.username,
        'name': creator.fullname
    }, request_headers)
