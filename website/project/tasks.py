from django.apps import apps
import logging
import urlparse
import random
import requests

from framework.celery_tasks import app as celery_app

from website import settings, mails
from website.util.share import GraphNode, format_contributor


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
    if bool({'spam_status', 'is_deleted'}.intersection(saved_fields)):
        need_update = True
    elif not node.is_public and 'is_public' not in saved_fields:
        need_update = False

    if need_update:
        node.update_search()
        update_node_share(node)

    if node.get_identifier_value('doi') and bool(node.IDENTIFIER_UPDATE_FIELDS.intersection(saved_fields)):
        node.request_identifier_update(category='doi')

def update_node_share(node):
    # Wrapper that ensures share_url and token exist
    if settings.SHARE_URL:
        if not settings.SHARE_API_TOKEN:
            return logger.warning('SHARE_API_TOKEN not set. Could not send "{}" to SHARE.'.format(node._id))
        _update_node_share(node)

def _update_node_share(node):
    # Any modifications to this function may need to change _async_update_node_share
    data = serialize_share_node_data(node)
    resp = send_share_node_data(data)
    try:
        resp.raise_for_status()
    except Exception:
        if resp.status_code >= 500:
            _async_update_node_share.delay(node._id)
        else:
            send_desk_share_error(node, resp, 0)

@celery_app.task(bind=True, max_retries=4, acks_late=True)
def _async_update_node_share(self, node_id):
    # Any modifications to this function may need to change _update_node_share
    # Takes node_id to ensure async retries push fresh data
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)

    data = serialize_share_node_data(node)
    resp = send_share_node_data(data)
    try:
        resp.raise_for_status()
    except Exception as e:
        if resp.status_code >= 500:
            if self.request.retries == self.max_retries:
                send_desk_share_error(node, resp, self.request.retries)
            raise self.retry(
                exc=e,
                countdown=(random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 10)
            )
        else:
            send_desk_share_error(node, resp, self.request.retries)

def send_share_node_data(data):
    resp = requests.post('{}api/normalizeddata/'.format(settings.SHARE_URL), json=data, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN), 'Content-Type': 'application/vnd.api+json'})
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
    is_qa_node = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(node.tags.all().values_list('name', flat=True))) \
        or any(substring in node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
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
    is_qa_node = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(node.tags.all().values_list('name', flat=True))) \
        or any(substring in node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])

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
        GraphNode('workidentifier', creative_work=registration_graph, uri=urlparse.urljoin(settings.DOMAIN, node.url))
    ]

    registration_graph.attrs['tags'] = [
        GraphNode('throughtags', creative_work=registration_graph, tag=GraphNode('tag', name=tag._id))
        for tag in node.tags.all() or [] if tag._id
    ]

    to_visit.extend(format_contributor(registration_graph, user, bool(user._id in node.visible_contributor_ids), i) for i, user in enumerate(node.contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=registration_graph, agent=GraphNode('institution', name=institution.name)) for institution in node.affiliated_institutions.all())

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
