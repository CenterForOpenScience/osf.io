from django.contrib import admin, messages
from django.urls import re_path
from django.template.response import TemplateResponse
from django_extensions.admin import ForeignKeyAutocompleteAdmin
from django.contrib.auth.models import Group
from django.db.models import Q, Count
from django.http import HttpResponseRedirect
from django.urls import reverse

from osf.external.spam.tasks import reclassify_domain_references
from osf.models import OSFUser, Node, NotableDomain, NodeLicense
from osf.models.notable_domain import DomainReference


def list_displayable_fields(cls):
    return [x.name for x in cls._meta.fields if x.editable and not x.is_relation and not x.primary_key]

class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = list_displayable_fields(Node)

class OSFUserAdmin(admin.ModelAdmin):
    fields = ['groups', 'user_permissions'] + list_displayable_fields(OSFUser)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Restricts preprint/node/osfgroup django groups from showing up in the user's groups list in the admin app
        """
        if db_field.name == 'groups':
            kwargs['queryset'] = Group.objects.exclude(Q(name__startswith='preprint_') | Q(name__startswith='node_') | Q(name__startswith='osfgroup_') | Q(name__startswith='collections_'))
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        """
        Since m2m fields overridden with new form data in admin app, preprint groups/node/osfgroup groups (which are now excluded from being selections)
        are removed.  Manually re-adds preprint/node groups after adding new groups in form.
        """
        groups_to_preserve = list(form.instance.groups.filter(Q(name__startswith='preprint_') | Q(name__startswith='node_') | Q(name__startswith='osfgroup_') | Q(name__startswith='collections_')))
        super().save_related(request, form, formsets, change)
        if 'groups' in form.cleaned_data:
            for group in groups_to_preserve:
                form.instance.groups.add(group)


class LicenseAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(NodeLicense)


class NotableDomainAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(NotableDomain)
    ordering = ('-id',)
    list_display = ('domain', 'note', 'number_of_references')
    list_filter = ('note',)
    search_fields = ('domain',)
    actions = ['make_ignored', 'make_excluded']

    @admin.display(ordering='number_of_references')
    def number_of_references(self, obj):
        return obj.number_of_references

    @admin.action(description='Mark selected as IGNORED')
    def make_ignored(self, request, queryset):
        signatures = []
        target_note = 3  # IGNORED
        for obj in queryset:
            signatures.append({
                'notable_domain_id': obj.pk,
                'current_note': target_note,
                'previous_note': obj.note
            })
        queryset.update(note=target_note)
        for sig in signatures:
            reclassify_domain_references.apply_async(kwargs=sig)

    @admin.action(description='Mark selected as EXCLUDED')
    def make_excluded(self, request, queryset):
        signatures = []
        target_note = 0  # EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        for obj in queryset:
            signatures.append({
                'notable_domain_id': obj.pk,
                'current_note': target_note,
                'previous_note': obj.note
            })
        queryset.update(note=target_note)
        for sig in signatures:
            reclassify_domain_references.apply_async(kwargs=sig)

    def get_urls(self):
        urls = super().get_urls()
        return [
            re_path(
                r'^bulkadd/$',
                self.admin_site.admin_view(self.bulk_add_view),
                name='osf_notabledomain_bulkadd',
            ),
            *urls,
        ]

    def bulk_add_view(self, request):
        if request.method == 'GET':

            context = {
                **self.admin_site.each_context(request),
                'note_choices': list(NotableDomain.Note),
            }
            return TemplateResponse(request, 'admin/osf/notabledomain/bulkadd.html', context)

        if request.method == 'POST':
            domains = filter(
                None,  # remove empty lines
                request.POST['notable_email_domains'].split('\n'),
            )
            num_added = self._bulk_add(domains, request.POST['note'])
            self.message_user(
                request,
                f'Success! {num_added} notable email domains added!',
                messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse('admin:osf_notabledomain_changelist'))

    def _bulk_add(self, domain_names, note):
        num_added = 0
        for domain_name in domain_names:
            domain_name = domain_name.strip().lower()
            if domain_name:
                num_added += 1
                NotableDomain.objects.update_or_create(
                    domain=domain_name,
                    defaults={
                        'note': note,
                    },
                )
        return num_added

    def change_view(self, request, object_id, form_url='', extra_context=None):
        references = DomainReference.objects.filter(domain_id=object_id)
        return self.changeform_view(request, object_id, form_url, {'references': references})

    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(number_of_references=Count('domainreference'))
        return qs

admin.site.register(OSFUser, OSFUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(NotableDomain, NotableDomainAdmin)
admin.site.register(NodeLicense, LicenseAdmin)
