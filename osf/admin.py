from django.contrib import admin
from django_extensions.admin import ForeignKeyAutocompleteAdmin
from django.contrib.auth.models import Group

from osf.models import OSFUser, Node, BlacklistedEmailDomain


def list_displayable_fields(cls):
    return [x.name for x in cls._meta.fields if x.editable and not x.is_relation and not x.primary_key]

class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = list_displayable_fields(Node)

class OSFUserAdmin(admin.ModelAdmin):
    fields = ['groups', 'user_permissions'] + list_displayable_fields(OSFUser)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Restricts preprint django groups from showing up in the user's groups list in the admin app
        """
        if db_field.name == 'groups':
            kwargs['queryset'] = Group.objects.exclude(name__startswith='preprint_')
        return super(OSFUserAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        """
        Since m2m fields overridden with new form data in admin app, preprint groups (which are now excluded from being selections)
        are removed.  Manually re-adds preprint groups after adding new groups in form.
        """
        preprint_groups = list(form.instance.groups.filter(name__startswith='preprint_'))
        super(OSFUserAdmin, self).save_related(request, form, formsets, change)
        if 'groups' in form.cleaned_data:
            for group in preprint_groups:
                form.instance.groups.add(group)

class BlacklistedEmailDomainAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(BlacklistedEmailDomain)
    ordering = ('domain', )

admin.site.register(OSFUser, OSFUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(BlacklistedEmailDomain, BlacklistedEmailDomainAdmin)
