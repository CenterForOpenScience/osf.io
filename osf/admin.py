from django.contrib import admin, messages
from django.conf.urls import url
from django.template.response import TemplateResponse
from django_extensions.admin import ForeignKeyAutocompleteAdmin
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse

from osf.models import OSFUser, Node, NotableEmailDomain, NodeLicense


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
        return super(OSFUserAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        """
        Since m2m fields overridden with new form data in admin app, preprint groups/node/osfgroup groups (which are now excluded from being selections)
        are removed.  Manually re-adds preprint/node groups after adding new groups in form.
        """
        groups_to_preserve = list(form.instance.groups.filter(Q(name__startswith='preprint_') | Q(name__startswith='node_') | Q(name__startswith='osfgroup_') | Q(name__startswith='collections_')))
        super(OSFUserAdmin, self).save_related(request, form, formsets, change)
        if 'groups' in form.cleaned_data:
            for group in groups_to_preserve:
                form.instance.groups.add(group)


class LicenseAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(NodeLicense)


class NotableEmailDomainAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(NotableEmailDomain)
    ordering = ('-id',)
    list_display = ('domain', 'note')
    list_filter = ('note',)
    search_fields = ('domain',)

    def get_urls(self):
        urls = super().get_urls()
        return [
            url(
                r'^bulkadd/$',
                self.admin_site.admin_view(self.bulk_add_view),
                name='osf_notableemaildomain_bulkadd',
            ),
            *urls,
        ]

    def bulk_add_view(self, request):
        if request.method == 'GET':

            context = {
                **self.admin_site.each_context(request),
                'note_choices': list(NotableEmailDomain.Note),
            }
            return TemplateResponse(request, 'admin/osf/notableemaildomain/bulkadd.html', context)

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
            return HttpResponseRedirect(reverse('admin:osf_notableemaildomain_changelist'))

    def _bulk_add(self, domain_names, note):
        num_added = 0
        for domain_name in domain_names:
            domain_name = domain_name.strip().lower()
            if domain_name:
                num_added += 1
                NotableEmailDomain.objects.update_or_create(
                    domain=domain_name,
                    defaults={
                        'note': note,
                    },
                )
        return num_added


admin.site.register(OSFUser, OSFUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(NotableEmailDomain, NotableEmailDomainAdmin)
admin.site.register(NodeLicense, LicenseAdmin)
