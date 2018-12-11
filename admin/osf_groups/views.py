from admin.osf_groups.serializers import serializer_group

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import FormView, DetailView, ListView
from osf.models import OSFGroup
from admin.osf_groups.forms import OSFGroupSearchForm
from django.core.urlresolvers import reverse
from django.contrib import messages


class OSFGroupsView(PermissionRequiredMixin, DetailView):
    """ Allow authorized admin user to view nodes

    View of OSF database. No admin models.
    """
    template_name = 'osf_groups/osf_groups.html'
    context_object_name = 'group'
    permission_required = 'osf.view_osf_groups'
    raise_exception = True

    def get_object(self, queryset=None):
        id = self.kwargs.get('id')
        osf_group = OSFGroup.objects.get(id=id)
        return serializer_group(osf_group)


class OSFGroupsFormView(PermissionRequiredMixin, FormView):
    template_name = 'osf_groups/search.html'
    object_type = 'osf_group'
    permission_required = 'osf.view_osf_groups'
    raise_exception = True
    form_class = OSFGroupSearchForm

    def __init__(self):
        self.redirect_url = None
        super(OSFGroupsFormView, self).__init__()

    def form_valid(self, form):
        id = form.data.get('id').strip()
        name = form.data.get('name').strip()

        if id:
            self.redirect_url = reverse('osf_groups:osf_group', kwargs={'id': id})
        elif name:
            try:
                group = OSFGroup.objects.get(name__contains=name)
                self.redirect_url = reverse('osf_groups:osf_group', kwargs={'id': group.id})
            except OSFGroup.MultipleObjectsReturned:
                self.redirect_url = reverse('osf_groups:osf_groups_list',) + '?name={}'.format(name)
            except OSFGroup.DoesNotExist:
                messages.error(self.request, 'That OSF Group could not be found')
                self.redirect_url = reverse('osf_groups:search')

        return super(OSFGroupsFormView, self).form_valid(form)

    @property
    def success_url(self):
        return self.redirect_url

class OSFGroupsListView(PermissionRequiredMixin, ListView):
    """ Allow authorized admin user to view list of registrations

    View of OSF database. No admin models.
    """
    template_name = 'osf_groups/osf_groups_list.html'
    paginate_by = 10
    paginate_orphans = 1
    context_object_name = 'osf_groups'
    permission_required = 'osf.view_osf_groups'
    raise_exception = True

    def get_queryset(self):
        name = self.request.GET.get('name')
        if name:
            return OSFGroup.objects.filter(name__contains=name)

        return OSFGroup.objects.all()

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)

        return {
            'groups': list(query_set),
            'page': page,
        }
