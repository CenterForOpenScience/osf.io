import logging
import urlparse

import requests

from framework.celery_tasks import app as celery_app

from website import settings
from website.util.share import GraphNode, format_contributor

from website.identifiers.utils import request_identifiers_from_ezid, get_ezid_client, build_ezid_metadata, parse_identifiers

logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def on_preprint_updated(preprint_id, update_share=False):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    from osf.models import PreprintService
    preprint = PreprintService.load(preprint_id)

    if preprint.node:
        status = 'public' if preprint.node.is_public else 'unavailable'
        update_ezid_metadata_on_change(preprint, status=status)

    if settings.SHARE_URL and update_share:
        if not preprint.provider.access_token:
            raise ValueError('No access_token for {}. Unable to send {} to SHARE.'.format(preprint.provider, preprint))
        resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'tasks': [],
                    'raw': None,
                    'data': {'@graph': format_preprint(preprint)}
                }
            }
        }, headers={'Authorization': 'Bearer {}'.format(preprint.provider.access_token), 'Content-Type': 'application/vnd.api+json'})
        logger.debug(resp.content)
        resp.raise_for_status()

def format_preprint(preprint):
    preprint_graph = GraphNode('preprint', **{
        'title': preprint.node.title,
        'description': preprint.node.description or '',
        'is_deleted': (
            not preprint.is_published or
            not preprint.node.is_public or
            preprint.node.is_preprint_orphan or
            preprint.node.tags.filter(name='qatest').exists() or
            preprint.node.is_deleted
        ),
        'date_updated': preprint.date_modified.isoformat(),
        'date_published': preprint.date_published.isoformat() if preprint.date_published else None
    })

    to_visit = [
        preprint_graph,
        GraphNode('workidentifier', creative_work=preprint_graph, uri=urlparse.urljoin(settings.DOMAIN, preprint._id + '/'))
    ]

    if preprint.get_identifier('doi'):
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri='http://dx.doi.org/{}'.format(preprint.get_identifier('doi').value)))

    if preprint.provider.domain_redirect_enabled:
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri=preprint.absolute_url))

    if preprint.article_doi:
        # Article DOI refers to a clone of this preprint on another system and therefore does not qualify as an identifier for this preprint
        related_work = GraphNode('creativework')
        to_visit.append(GraphNode('workrelation', subject=preprint_graph, related=related_work))
        to_visit.append(GraphNode('workidentifier', creative_work=related_work, uri='http://dx.doi.org/{}'.format(preprint.article_doi)))

    preprint_graph.attrs['tags'] = [
        GraphNode('throughtags', creative_work=preprint_graph, tag=GraphNode('tag', name=tag))
        for tag in preprint.node.tags.values_list('name', flat=True) if tag
    ]

    preprint_graph.attrs['subjects'] = [
        GraphNode('throughsubjects', creative_work=preprint_graph, subject=GraphNode('subject', name=subject))
        for subject in set(s.bepress_text for s in preprint.subjects.all())
    ]

    to_visit.extend(format_contributor(preprint_graph, user, preprint.node.get_visible(user), i) for i, user in enumerate(preprint.node.contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=preprint_graph, agent=GraphNode('institution', name=institution))
                    for institution in preprint.node.affiliated_institutions.values_list('name', flat=True))

    visited = set()
    to_visit.extend(preprint_graph.get_related())

    while True:
        if not to_visit:
            break
        n = to_visit.pop(0)
        if n in visited:
            continue
        visited.add(n)
        to_visit.extend(list(n.get_related()))

    return [node.serialize() for node in visited]


@celery_app.task(ignore_results=True)
def get_and_set_preprint_identifiers(preprint_id):
    from osf.models import PreprintService

    preprint = PreprintService.load(preprint_id)
    ezid_response = request_identifiers_from_ezid(preprint)
    id_dict = parse_identifiers(ezid_response)
    preprint.set_identifier_values(doi=id_dict['doi'], ark=id_dict['ark'])


@celery_app.task(ignore_results=True)
def update_ezid_metadata_on_change(target_object, status):
    if (settings.EZID_USERNAME and settings.EZID_PASSWORD) and target_object.get_identifier('doi'):
        client = get_ezid_client()

        doi, metadata = build_ezid_metadata(target_object)
        client.change_status_identifier(status, doi, metadata)
