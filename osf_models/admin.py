from django.contrib import admin
from django_extensions.admin import ForeignKeyAutocompleteAdmin

from osf_models.models import *
from osf_models import models
import inspect

from django.db.models.base import ModelBase
from django.contrib.admin.sites import AlreadyRegistered


class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = (
        'title',
        'description',
        'category',
        'is_public',
        # 'creator',
        # 'contributors',
        # 'users_watching_node',
        'tags',
        'system_tags',
        # 'nodes',
        # 'parent_node',
        # 'template_node',
        'piwik_site_id',
        'child_node_subscriptions',
        'institution_id',
        'institution_domains',
        'institution_auth_url',
        'institution_logo_name',
        'institution_email_domains',
        # '_primary_institution',
        # '_affiliated_institutions',
        'is_deleted',
        'deleted_date',
        'is_registration',
        'registered_date',
        # 'registered_user',
        'registered_schema',
        'registered_meta',
        'registration_approval',
        # 'registered_from',
        'embargo',
        'is_fork',
        # 'forked_from',
        'forked_date',
        'public_comments',
        'wiki_pages_current',
        'wiki_pages_versions',
        'wiki_private_uuids',
        'file_guid_to_share_uuids',
        'date_created',
        'date_modified', )


admin.site.register(Node, NodeAdmin)

for name, obj in inspect.getmembers(models):
    if inspect.isclass(obj):
        if isinstance(obj, ModelBase):
            if not obj._meta.abstract:
                try:
                    admin.site.register(obj)
                except AlreadyRegistered:
                    pass
