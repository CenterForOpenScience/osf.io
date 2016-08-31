from celery.utils.log import get_task_logger

from framework.celery_tasks import app as celery_app

from website import settings
from website.util import akismet

logger = get_task_logger(__name__)


@celery_app.task
def _check_for_spam(node_id, content, author_info, request_headers, flag=True):
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
        logger.info("Node '{}' ({}) smells like spam".format(node.title, node._id))
        if flag:
            node.flag_spam(save=True)
        else:
            return True
    else:
        logger.info('Node {} smells like ham'.format(node_id))
        return False

def check_node_for_spam(document, creator, request_headers, flag=True, async=True):
    content = """
    {}

    {}

    {}
    """.format(
        document['title'],
        document['description'],
        '\n'.join(document['wikis'].values())
    )

    if async:
        _check_for_spam.delay(document['id'], content, {
            'email': creator.username,
            'name': creator.fullname
        }, request_headers)
    else:
        return _check_for_spam(document['id'], content, {
            'email': creator.username,
            'name': creator.fullname
        }, request_headers)
