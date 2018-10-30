from django.contrib import admin
from django_extensions.admin import ForeignKeyAutocompleteAdmin
from django.contrib.auth.models import Group
from osf.models import *  # noqa


def list_displayable_fields(cls):
    return [x.name for x in cls._meta.fields if x.editable and not x.is_relation and not x.primary_key]

class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = list_displayable_fields(Node)

class OSFUserAdmin(admin.ModelAdmin):
    fields = ['groups', 'user_permissions'] + list_displayable_fields(OSFUser)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'groups':
            kwargs['queryset'] = Group.objects.exclude(name__startswith='preprint_')
        return super(OSFUserAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

admin.site.register(OSFUser, OSFUserAdmin)
admin.site.register(Node, NodeAdmin)
