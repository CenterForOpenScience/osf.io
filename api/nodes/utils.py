# -*- coding: utf-8 -*-
from distutils.version import StrictVersion
from django.apps import apps
from django.db.models import Q, OuterRef, Exists, Subquery, CharField, Value, BooleanField
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.status import is_server_error
import requests

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder, NodeSettings, Region
from addons.wiki.models import NodeSettings as WikiNodeSettings
from osf.models import AbstractNode, Preprint, Guid, NodeRelation, Contributor
from osf.models.node import NodeGroupObjectPermission
from osf.utils import permissions

from api.base.exceptions import ServiceUnavailableError
from api.base.utils import get_object_or_error, waterbutler_api_url_for, get_user_auth, has_admin_scope

def get_file_object(target, path, provider, request):
    # Don't bother going to waterbutler for osfstorage
    if provider == 'osfstorage':
        # Kinda like /me for a user
        # The one odd case where path is not really path
        if path == '/':
            if isinstance(target, AbstractNode):
                obj = target.get_addon('osfstorage').get_root()
            elif isinstance(target, Preprint):
                obj = target.root_folder
            else:
                obj = target
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

    ***Use with caution - while # of queries are reduced, at scale, this can
    slow down the request significantly**
    """
    def optimize_node_queryset(self, queryset):
        OSFUserGroup = apps.get_model('osf', 'osfuser_groups')

        auth = get_user_auth(self.request)
        admin_scope = has_admin_scope(self.request)
        abstract_node_contenttype_id = ContentType.objects.get_for_model(AbstractNode).id
        guid = Guid.objects.filter(content_type_id=abstract_node_contenttype_id, object_id=OuterRef('parent_id'))
        parent = NodeRelation.objects.annotate(parent__id=Subquery(guid.values('_id')[:1])).filter(child=OuterRef('pk'), is_node_link=False)
        wiki_addon = WikiNodeSettings.objects.filter(owner=OuterRef('pk'), is_deleted=False)
        preprints = Preprint.objects.can_view(user=auth.user).filter(node_id=OuterRef('pk'))
        region = Region.objects.filter(id=OuterRef('region_id'))
        node_settings = NodeSettings.objects.annotate(region_abbrev=Subquery(region.values('_id')[:1])).filter(owner_id=OuterRef('pk'))

        admin_permission = Permission.objects.get(codename=permissions.ADMIN_NODE)
        write_permission = Permission.objects.get(codename=permissions.WRITE_NODE)
        read_permission = Permission.objects.get(codename=permissions.READ_NODE)
        contrib = Contributor.objects.filter(user=auth.user, node=OuterRef('pk'))
        user_group = OSFUserGroup.objects.filter(osfuser_id=auth.user.id if auth.user else None, group_id=OuterRef('group_id'))
        node_group = NodeGroupObjectPermission.objects.annotate(user_group=Subquery(user_group.values_list('group_id')[:1])).filter(user_group__isnull=False, content_object_id=OuterRef('pk'))
        # user_is_contrib means user is a traditional contributor, while has_read/write/admin are permissions the user has either through group membership or contributorship
        return queryset.prefetch_related('root').prefetch_related('subjects').annotate(
            user_is_contrib=Exists(contrib),
            has_read=Exists(node_group.filter(permission_id=read_permission.id)),
            has_write=Exists(node_group.filter(permission_id=write_permission.id)),
            has_admin=Exists(node_group.filter(permission_id=admin_permission.id)),
            has_wiki_addon=Exists(wiki_addon),
            annotated_parent_id=Subquery(parent.values('parent__id')[:1], output_field=CharField()),
            has_viewable_preprints=Exists(preprints),
            has_admin_scope=Value(admin_scope, output_field=BooleanField()),
            region=Subquery(node_settings.values('region_abbrev')[:1]),
        )
