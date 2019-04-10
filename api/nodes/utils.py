# -*- coding: utf-8 -*-
from distutils.version import StrictVersion

from django.db.models import Q, OuterRef, Exists, Subquery, CharField, Value, BooleanField
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.status import is_server_error
import requests

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder
from addons.wiki.models import NodeSettings as WikiNodeSettings
from osf.models import AbstractNode, Guid, NodeRelation, Contributor


from api.base.exceptions import ServiceUnavailableError
from api.base.utils import get_object_or_error, waterbutler_api_url_for, get_user_auth, has_admin_scope

def get_file_object(target, path, provider, request):
    # Don't bother going to waterbutler for osfstorage
    if provider == 'osfstorage':
        # Kinda like /me for a user
        # The one odd case where path is not really path
        if path == '/':
            obj = target.get_root_folder(provider=provider)
        else:
            if path.endswith('/'):
                model = OsfStorageFolder
            else:
                model = OsfStorageFile
            content_type = ContentType.objects.get_for_model(target)
            obj = get_object_or_error(model, Q(target_object_id=target.pk, target_content_type=content_type, _id=path.strip('/')), request)
        return obj

    if isinstance(target, AbstractNode) and not target.get_addon(provider) or not target.get_addon(provider).configured:
        raise NotFound('The {} provider is not configured for this project.'.format(provider))

    view_only = request.query_params.get('view_only', default=None)
    base_url = None
    if hasattr(target, 'osfstorage_region'):
        base_url = target.osfstorage_region.waterbutler_url
    url = waterbutler_api_url_for(
        target._id, provider, path, _internal=True,
        base_url=base_url, meta=True, view_only=view_only,
    )

    waterbutler_request = requests.get(
        url,
        cookies=request.COOKIES,
        headers={'Authorization': request.META.get('HTTP_AUTHORIZATION')},
    )

    if waterbutler_request.status_code == 401:
        raise PermissionDenied

    if waterbutler_request.status_code == 404:
        raise NotFound

    if is_server_error(waterbutler_request.status_code):
        raise ServiceUnavailableError(detail='Could not retrieve files information at this time.')

    try:
        return waterbutler_request.json()['data']
    except KeyError:
        raise ServiceUnavailableError(detail='Could not retrieve files information at this time.')

def enforce_no_children(request):
    return StrictVersion(request.version) < StrictVersion('2.12')

class NodeOptimizationMixin(object):
    """Mixin with convenience method for optimizing serialization of nodes.
    Annotates the node queryset with several properties to reduce number of queries.
    """
    def optimize_node_queryset(self, queryset):
        auth = get_user_auth(self.request)
        admin_scope = has_admin_scope(self.request)
        abstract_node_contenttype_id = ContentType.objects.get_for_model(AbstractNode).id
        guid = Guid.objects.filter(content_type_id=abstract_node_contenttype_id, object_id=OuterRef('parent_id'))
        parent = NodeRelation.objects.annotate(parent__id=Subquery(guid.values('_id')[:1])).filter(child=OuterRef('pk'), is_node_link=False)
        wiki_addon = WikiNodeSettings.objects.filter(owner=OuterRef('pk'), deleted=False)
        contribs = Contributor.objects.filter(user=auth.user, node=OuterRef('pk'))
        return queryset.prefetch_related('root').prefetch_related('subjects').annotate(
            user_is_contrib=Exists(contribs),
            contrib_read=Subquery(contribs.values('read')[:1]),
            contrib_write=Subquery(contribs.values('write')[:1]),
            contrib_admin=Subquery(contribs.values('admin')[:1]),
            has_wiki_addon=Exists(wiki_addon),
            annotated_parent_id=Subquery(parent.values('parent__id')[:1], output_field=CharField()),
            annotated_tags=ArrayAgg('tags__name'),
            has_admin_scope=Value(admin_scope, output_field=BooleanField()),
        )
