from django.apps import apps
import httplib as http
import logging
import pytz
import urlparse
import random
import requests
import celery

from framework.celery_tasks.handlers import enqueue_task
from dateutil.parser import parse as parse_date
from django.utils import timezone

from framework import status
from framework.celery_tasks import app as celery_app
from framework.exceptions import HTTPError

from osf.exceptions import ValidationValueError
from osf.models.node_relation import NodeRelation

from website import settings, mails
from website.exceptions import NodeStateError
from website.project import signals as project_signals
from website.util.share import GraphNode, format_contributor


logger = logging.getLogger(__name__)

def on_node_register(original, draft=None, auth=None, data=None, schema=None, parent=None, reg_choice=None, celery=True):
    if celery:
        return enqueue_task(_on_node_register_celery.s(original, draft=draft, auth=auth, data=data, schema=schema, parent=parent, reg_choice=reg_choice, celery=celery))
    return _on_node_register(original, draft=draft, auth=auth, data=data, schema=schema, parent=parent, reg_choice=reg_choice, celery=celery)

@celery_app.task(ignore_results=False)
def _on_node_register_celery(original, draft=None, auth=None, data=None, schema=None, parent=None, reg_choice=None, celery=True):
    _on_node_register(original, draft=draft, auth=auth, data=data, schema=schema, parent=parent, reg_choice=reg_choice, celery=celery)

def _on_node_register(original, draft=None, auth=None, data=None, schema=None, parent=None, reg_choice=None, celery=True):
    registered = original.clone()
    registered.recast('osf.registration')

    registered.registered_date = timezone.now()
    registered.registered_user = auth.user
    registered.registered_from = original
    if not registered.registered_meta:
        registered.registered_meta = {}
    registered.registered_meta[schema._id] = data

    registered.forked_from = original.forked_from
    registered.creator = original.creator
    registered.node_license = original.license.copy() if original.license else None
    registered.wiki_private_uuids = {}

    # Need to save here in order to set many-to-many fields
    registered.save()

    registered.registered_schema.add(schema)
    registered.copy_contributors_from(original)
    registered.tags.add(*original.all_tags.values_list('pk', flat=True))
    registered.affiliated_institutions.add(*original.affiliated_institutions.values_list('pk', flat=True))

    # Clone each log from the original node for this registration.
    logs = original.logs.all()
    for log in logs:
        log.clone_node_log(registered._id)

    registered.is_public = False

    for node in registered.get_descendants_recursive():
        node.is_public = False
        node.save()

    if parent:
        node_relation = NodeRelation.objects.get(parent=parent.registered_from, child=original)
        NodeRelation.objects.get_or_create(_order=node_relation._order, parent=parent, child=registered)

    # After register callback
    for addon in original.get_addons():
        _, message = addon.after_register(original, registered, auth.user)
        if message:
            status.push_status_message(message, kind='info', trust=False)

    for node_relation in original.node_relations.filter(child__is_deleted=False):
        node_contained = node_relation.child
        # Register child nodes
        if not node_relation.is_node_link:
            registered_child = node_contained.register_node(  # noqa
                schema=schema,
                auth=auth,
                data=data,
                parent=registered,
                celery=celery)
        else:
            # Copy linked nodes
            NodeRelation.objects.get_or_create(
                is_node_link=True,
                parent=registered,
                child=node_contained
            )

    registered.root = None  # Recompute root on save

    registered.save()

    if settings.ENABLE_ARCHIVER:
        registered.refresh_from_db()
        project_signals.after_create_registration.send(original, dst=registered, user=auth.user)

    if parent is None:
        DraftRegistrationLog = apps.get_model('osf.DraftRegistrationLog')

        draft.registered_node = registered
        draft.add_status_log(auth.user, DraftRegistrationLog.REGISTERED)

        save = False
        if save:
            draft.save()

        if reg_choice == 'embargo':
            # Initiate embargo
            embargo_end_date = parse_date(data['embargoEndDate'], ignoretz=True).replace(tzinfo=pytz.utc)
            try:
                registered.embargo_registration(auth.user, embargo_end_date)
            except ValidationValueError as err:
                raise HTTPError(http.BAD_REQUEST, data=dict(message_long=err.message))
        elif reg_choice == 'immediate':
            try:
                registered.require_approval(auth.user)
            except NodeStateError as err:
                raise HTTPError(http.BAD_REQUEST, data=dict(message_long=err.message))

    return registered

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
    return [
        {
            '@id': '_:123',
            '@type': 'workidentifier',
            'creative_work': {'@id': '_:789', '@type': 'project'},
            'uri': '{}{}/'.format(settings.DOMAIN, node._id),
        }, {
            '@id': '_:789',
            '@type': 'project',
            'is_deleted': not node.is_public or node.is_deleted or node.is_spammy,
        }
    ]

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

def send_desk_share_error(node, resp, retries):
    mails.send_mail(
        to_addr=settings.SUPPORT_EMAIL,
        mail=mails.SHARE_ERROR_DESK,
        node=node,
        resp=resp,
        retries=retries,
    )
