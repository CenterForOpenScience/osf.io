from django.contrib import admin
from django_extensions.admin import ForeignKeyAutocompleteAdmin

from osf.models import *  # noqa


class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = (
        'affiliated_institutions',
        'alternative_citations',
        'category',
        'creator',
        'deleted_date',
        'description',
        'forked_from',
        'is_deleted',
        'is_fork',
        'is_public',
        'keenio_read_key',
        'node_license',
        'piwik_site_id',
        'preprint_article_doi',
        'preprint_file',
        'public_comments',
        'suspended',
        'tags',
        'template_node',
        'title',
        'type',
        'wiki_pages_current',
        'wiki_pages_versions',
        'wiki_private_uuids',
        '_has_abandoned_preprint',
        '_is_preprint_orphan',
    )

admin.site.register(Node, NodeAdmin)  # noqa
admin.site.register(OSFUser)
