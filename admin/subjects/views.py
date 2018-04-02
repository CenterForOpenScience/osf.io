from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse_lazy
from django.views.generic import ListView, UpdateView

from admin.subjects.forms import SubjectForm
from osf.models.subject import Subject
from osf.models.provider import PreprintProvider


class SubjectListView(PermissionRequiredMixin, ListView):
    model = Subject
    permission_required = 'osf.view_subject'
    paginate_by = 100
    raise_exception = True

    def get_queryset(self):
        req_obj = self.request.GET
        qs = super(SubjectListView, self).get_queryset().order_by('text')
        if PreprintProvider.objects.filter(_id=req_obj.get('provider_id')).exists():
            qs = qs.filter(provider___id=req_obj.get('provider_id'))
        return qs

    def get_context_data(self, **kwargs):
        context = super(SubjectListView, self).get_context_data(**kwargs)
        context['filterable_provider_ids'] = dict({'': '---'}, **dict(PreprintProvider.objects.values_list('_id', 'name')))
        return context

class SubjectUpdateView(PermissionRequiredMixin, UpdateView):
    form_class = SubjectForm
    model = SubjectForm.Meta.model
    permission_required = 'osf.change_subject'
    raise_exception = True

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('subjects:list')
