from django.apps import apps
import logging
import urlparse

import random
import requests

from framework.exceptions import HTTPError
from framework.celery_tasks import app as celery_app
from framework import sentry

from website import settings, mails
from website.util.share import GraphNode, format_contributor, format_subject

from website.identifiers.utils import request_identifiers_from_ezid, get_ezid_client, build_ezid_metadata, parse_identifiers

logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def on_preprint_updated(preprint_id, update_share=True, share_type=None, old_subjects=None):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    from osf.models import PreprintService
    preprint = PreprintService.load(preprint_id)
    if old_subjects is None:
        old_subjects = []
    if preprint.node:
        status = 'public' if preprint.verified_publishable else 'unavailable'
        try:
            update_ezid_metadata_on_change(preprint, status=status)
        except HTTPError as err:
            sentry.log_exception()
            sentry.log_message(err.args[0])
    if update_share:
        update_preprint_share(preprint, old_subjects, share_type)

def update_preprint_share(preprint, old_subjects=None, share_type=None):
    if settings.SHARE_URL:
        if not preprint.provider.access_token:
            raise ValueError('No access_token for {}. Unable to send {} to SHARE.'.format(preprint.provider, preprint))
        share_type = share_type or preprint.provider.share_publish_type
        _update_preprint_share(preprint, old_subjects, share_type)

def _update_preprint_share(preprint, old_subjects, share_type):
    # Any modifications to this function may need to change _async_update_preprint_share
    data = serialize_share_preprint_data(preprint, share_type, old_subjects)
    resp = send_share_preprint_data(preprint, data)
    try:
        resp.raise_for_status()
    except Exception:
        if resp.status_code >= 500:
            _async_update_preprint_share.delay(preprint._id, old_subjects)
        else:
            send_desk_share_preprint_error(preprint, resp, 0)

@celery_app.task(bind=True, max_retries=4, acks_late=True)
def _async_update_preprint_share(self, preprint_id, old_subjects, share_type):
    # Any modifications to this function may need to change _update_preprint_share
    # Takes preprint_id to ensure async retries push fresh data
    PreprintService = apps.get_model('osf.PreprintService')
    preprint = PreprintService.load(preprint_id)

    data = serialize_share_preprint_data(preprint, share_type, old_subjects)
    resp = send_share_preprint_data(preprint, data)
    try:
        resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'tasks': [],
                    'raw': None,
                    'data': {'@graph': format_preprint(preprint, share_type, old_subjects)}
                }
            }
        }, headers={'Authorization': 'Bearer {}'.format(preprint.provider.access_token), 'Content-Type': 'application/vnd.api+json'})
        logger.debug(resp.content)
        resp.raise_for_status()
    except Exception as e:
        if resp.status_code >= 500:
            if self.request.retries == self.max_retries:
                send_desk_share_preprint_error(preprint, resp, self.request.retries)
            raise self.retry(
                exc=e,
                countdown=(random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 10)
            )
        else:
            send_desk_share_preprint_error(preprint, resp, self.request.retries)

def serialize_share_preprint_data(preprint, share_type, old_subjects):
    return {
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'data': {'@graph': format_preprint(preprint, share_type, old_subjects)}
            }
        }
    }

def send_share_preprint_data(preprint, data):
    resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json=data, headers={'Authorization': 'Bearer {}'.format(preprint.provider.access_token), 'Content-Type': 'application/vnd.api+json'})
    logger.debug(resp.content)
    return resp

def format_preprint(preprint, share_type, old_subjects=None):
    if old_subjects is None:
        old_subjects = []
    from osf.models import Subject
    old_subjects = [Subject.objects.get(id=s) for s in old_subjects]
    preprint_graph = GraphNode(share_type, **{
        'title': preprint.node.title,
        'description': preprint.node.description or '',
        'is_deleted': (
            not preprint.verified_publishable or
            preprint.node.tags.filter(name='qatest').exists()
        ),
        # Note: Changing any preprint attribute that is pulled from the node, like title, will NOT bump
        # the preprint's date modified but will bump the node's date_modified.
        # We have to send the latest date to SHARE to actually get the result to be updated.
        # If we send a date_updated that is <= the one we previously sent, SHARE will ignore any changes
        # because it looks like a race condition that arose from preprints being resent to SHARE on
        # every step of preprint creation.
        'date_updated': max(preprint.date_modified, preprint.node.date_modified).isoformat(),
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

    current_subjects = [
        GraphNode('throughsubjects', creative_work=preprint_graph, is_deleted=False, subject=format_subject(s))
        for s in preprint.subjects.all()
    ]
    deleted_subjects = [
        GraphNode('throughsubjects', creative_work=preprint_graph, is_deleted=True, subject=format_subject(s))
        for s in old_subjects if not preprint.subjects.filter(id=s.id).exists()
    ]
    preprint_graph.attrs['subjects'] = current_subjects + deleted_subjects

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
def get_and_set_preprint_identifiers(preprint):
    ezid_response = request_identifiers_from_ezid(preprint)
    if ezid_response is None:
        return
    id_dict = parse_identifiers(ezid_response)
    preprint.set_identifier_values(doi=id_dict['doi'], ark=id_dict['ark'])


@celery_app.task(ignore_results=True)
def update_ezid_metadata_on_change(target_object, status):
    if (settings.EZID_USERNAME and settings.EZID_PASSWORD) and target_object.get_identifier('doi'):
        client = get_ezid_client()

        doi, metadata = build_ezid_metadata(target_object)
        client.change_status_identifier(status, doi, metadata)

def send_desk_share_preprint_error(preprint, resp, retries):
    mails.send_mail(
        to_addr=settings.SUPPORT_EMAIL,
        mail=mails.SHARE_PREPRINT_ERROR_DESK,
        preprint=preprint,
        resp=resp,
        retries=retries,
    )
