import logging
import random
import requests
from urllib.parse import urljoin

from django.apps import apps
from framework.celery_tasks import app as celery_app

from website import settings, mails
from api.share.utils import GraphNode, format_contributor, update_share

logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def on_node_updated(node_id, user_id, first_save, saved_fields, request_headers=None):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)

    if node.is_collection or node.archiving or node.is_quickfiles:
        return

    need_update = bool(node.SEARCH_UPDATE_FIELDS.intersection(saved_fields))
    # due to async nature of call this can issue a search update for a new record (acceptable trade-off)
    if bool({'spam_status', 'is_deleted', 'deleted'}.intersection(saved_fields)):
        need_update = True
    elif not node.is_public and 'is_public' not in saved_fields:
        need_update = False

    if need_update:
        node.update_search()
        if settings.SHARE_ENABLED:
            update_share(node)
        update_collecting_metadata(node, saved_fields)

    if node.get_identifier_value('doi') and bool(node.IDENTIFIER_UPDATE_FIELDS.intersection(saved_fields)):
        node.request_identifier_update(category='doi')


def update_collecting_metadata(node, saved_fields):
    from website.search.search import update_collected_metadata
    if node.is_collected:
        if node.is_public:
            update_collected_metadata(node._id)
        else:
            update_collected_metadata(node._id, op='delete')


def update_node_share(node):
    # Any modifications to this function may need to change _async_update_node_share
    if not settings.SHARE_URL or not settings.SHARE_API_TOKEN:
        logger.warning(f'SHARE_API_TOKEN not set. Could not send "{node._id}" to SHARE.')
        return

    resp = send_share_node_data(node)

    try:
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        if resp.status_code >= 500:
            _async_update_node_share.delay(node._id)
        else:
            send_desk_share_error(node, resp, 0)


def calculate_backoff_time_celery(retries):
    return (random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** retries, 60 * 10)


@celery_app.task(bind=True, max_retries=4, acks_late=True)
def _async_update_node_share(self, node_id):
    # Any modifications to this function may need to change _update_node_share
    # Takes node_id to ensure async retries push fresh data
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)
    request = self.request

    resp = send_share_node_data(node)

    try:
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        if resp.status_code >= 500:
            if self.request.retries == self.max_retries:
                send_desk_share_error(node, resp, request.retries)
            raise self.retry(
                exc=e,
                countdown=calculate_backoff_time_celery(request.retries)
            )
        else:
            send_desk_share_error(node, resp, self.request.retries)


def send_share_node_data(node):
    """
    Sends data about an updating node/registration data to SHARE for indexing.
    :param data: dictionary of XML data.
    :return:
    """
    data = serialize_share_node_data(node)

    if node.provider and getattr(node.provider, 'access_token'):
        token = node.provider.access_token
    else:
        token = settings.SHARE_API_TOKEN

    resp = requests.post(
        f'{settings.SHARE_URL}/api/normalizeddata/',
        json=data,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/vnd.api+json'
        }
    )

    logger.debug(resp.content)
    return resp


def serialize_share_node_data(node):
    return {
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'data': {'@graph': format_registration(node) if node.is_registration else format_node(node)}
            }
        }
    }


def format_node(node):
    is_qa_node = check_if_qa_node(node)
    return [
        {
            '@id': '_:123',
            '@type': 'workidentifier',
            'creative_work': {'@id': '_:789', '@type': 'project'},
            'uri': '{}{}/'.format(settings.DOMAIN, node._id),
        }, {
            '@id': '_:789',
            '@type': 'project',
            'is_deleted': not node.is_public or node.is_deleted or node.is_spammy or is_qa_node
        }
    ]


def format_registration(node):
    is_qa_node = check_if_qa_node(node)

    registration_graph = GraphNode('registration', **{
        'title': node.title,
        'description': node.description or '',
        'is_deleted': not node.is_public or node.is_deleted or is_qa_node,
        'date_published': node.registered_date.isoformat() if node.registered_date else None,
        'registration_type': node.registered_schema.first().name if node.registered_schema else None,
        'withdrawn': node.is_retracted,
        'justification': node.retraction.justification if node.retraction else None,
    })

    to_visit = [
        registration_graph,
        GraphNode('workidentifier', creative_work=registration_graph, uri=urljoin(settings.DOMAIN, node.url))
    ]

    registration_graph.attrs['tags'] = [
        GraphNode('throughtags', creative_work=registration_graph, tag=GraphNode('tag', name=tag._id))
        for tag in node.tags.all() or [] if tag._id
    ]

    to_visit.extend(format_contributor(registration_graph, user, bool(user._id in node.visible_contributor_ids), i) for i, user in enumerate(node.contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=registration_graph, agent=GraphNode('institution', name=institution.name)) for institution in node.affiliated_institutions.all())

    if node.parent_node:
        parent = GraphNode('registration')
        to_visit.extend([
            parent,
            GraphNode('workidentifier', creative_work=parent, uri=urljoin(settings.DOMAIN, node.parent_node.url)),
            GraphNode('ispartof', subject=registration_graph, related=parent),
        ])

    visited = set()
    to_visit.extend(registration_graph.get_related())

    while True:
        if not to_visit:
            break
        n = to_visit.pop(0)
        if n in visited:
            continue
        visited.add(n)
        to_visit.extend(list(n.get_related()))

    return [node_.serialize() for node_ in visited]


def send_desk_share_error(node, resp, retries):
    mails.send_mail(
        to_addr=settings.OSF_SUPPORT_EMAIL,
        mail=mails.SHARE_ERROR_DESK,
        node=node,
        resp=resp,
        retries=retries,
        can_change_preferences=False,
    )


def check_if_qa_node(node) -> bool:
    """
    Checks if a node or registration has a tag or title that shouldn't be indexed. QA uses these to test things on prod
    without effecting search results.
    :param node:
    :return: bool whether this is a QA test node.
    """
    node_tags = node.tags.all().values_list('name', flat=True)
    don_not_index_tags = set(settings.DO_NOT_INDEX_LIST['tags'])
    has_forbid_index_tags = bool(don_not_index_tags.intersection(node_tags))

    has_forbid_index_title = any(substring in node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])

    return has_forbid_index_tags or has_forbid_index_title
