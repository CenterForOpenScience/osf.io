from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.views.generic import FormView, DetailView
from django.views.defaults import page_not_found

from admin.base.forms import GuidForm
from admin.base.utils import osf_staff_check


@user_passes_test(osf_staff_check)
def home(request):
    context = {}
    return render(request, 'home.html', context)


class GuidFormView(FormView):
    form_class = GuidForm
    template_name = None
    object_type = None

    def __init__(self):
        self.guid = None
        super().__init__()

    def get_context_data(self, **kwargs):
        kwargs.setdefault('view', self)
        kwargs.setdefault('form', self.get_form())
        return kwargs

    def form_valid(self, form):
        self.guid = form.cleaned_data.get('guid').strip()
        return super().form_valid(form)

    @property
    def success_url(self):
        raise NotImplementedError


class GuidView(DetailView):
    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return page_not_found(
                request,
                AttributeError(f'resource with id "{kwargs.get("guid") or kwargs.get("id")}" not found.')
            )
