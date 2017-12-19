from django.contrib import admin
from django_extensions.admin import ForeignKeyAutocompleteAdmin

from osf.models import *  # noqa


def list_displayable_fields(cls):
    return [x.name for x in cls._meta.fields if x.editable and not x.is_relation and not x.primary_key]

class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = list_displayable_fields(Node)

class OSFUserAdmin(admin.ModelAdmin):
    fields = ['groups', 'user_permissions'] + list_displayable_fields(OSFUser)

admin.site.register(OSFUser, OSFUserAdmin)
admin.site.register(Node, NodeAdmin)
