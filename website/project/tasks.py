from django.apps import apps
import logging
import urlparse
import requests

from framework.celery_tasks import app as celery_app

from website import settings
from website.util.share import GraphNode, format_contributor


logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def on_node_updated(node_id, user_id, first_save, saved_fields, request_headers=None):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)

    if node.is_collection or node.archiving:
        return

    need_update = bool(node.SEARCH_UPDATE_FIELDS.intersection(saved_fields))
    # due to async nature of call this can issue a search update for a new record (acceptable trade-off)
    if bool({'spam_status', 'is_deleted'}.intersection(saved_fields)):
        need_update = True
    elif not node.is_public and 'is_public' not in saved_fields:
        need_update = False

    if need_update:
        node.update_search()

        if settings.SHARE_URL:
            if not settings.SHARE_API_TOKEN:
                return logger.warning('SHARE_API_TOKEN not set. Could not send %s to SHARE.'.format(node))
            if node.is_registration:
                on_registration_updated(node)
            else:
                resp = requests.post('{}api/normalizeddata/'.format(settings.SHARE_URL), json={
                    'data': {
                        'type': 'NormalizedData',
                        'attributes': {
                            'tasks': [],
                            'raw': None,
                            'data': {'@graph': [{
                                '@id': '_:123',
                                '@type': 'workidentifier',
                                'creative_work': {'@id': '_:789', '@type': 'project'},
                                'uri': '{}{}/'.format(settings.DOMAIN, node._id),
                            }, {
                                '@id': '_:789',
                                '@type': 'project',
                                'is_deleted': not node.is_public or node.is_deleted or node.is_spammy,
                            }]}
                        }
                    }
                }, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN), 'Content-Type': 'application/vnd.api+json'})
                logger.debug(resp.content)
                resp.raise_for_status()


def on_registration_updated(node):
    resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json={
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'data': {'@graph': format_registration(node)}
            }
        }
    }, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN), 'Content-Type': 'application/vnd.api+json'})
    logger.debug(resp.content)
    resp.raise_for_status()


def format_registration(node):
    registration_graph = GraphNode('registration', **{
        'title': node.title,
        'description': node.description or '',
        'is_deleted': not node.is_public or 'qatest' in (node.tags.all() or []) or node.is_deleted,
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
