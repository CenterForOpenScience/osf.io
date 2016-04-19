from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.generic import FormView, DetailView
from django.views.defaults import page_not_found

from admin.base.forms import GuidForm


@login_required
def home(request):
    context = {}
    return render(request, 'home.html', context)


class GuidFormView(FormView):
    form_class = GuidForm
    template_name = None
    object_type = None

    def __init__(self):
        self.guid = None
        super(GuidFormView, self).__init__()

    def get_context_data(self, **kwargs):
        kwargs.setdefault('view', self)
        kwargs.setdefault('form', self.get_form())
        return kwargs

    def form_valid(self, form):
        self.guid = form.cleaned_data.get('guid').strip()
        return super(GuidFormView, self).form_valid(form)

    @property
    def success_url(self):
        raise NotImplementedError


class GuidView(DetailView):
    def get(self, request, *args, **kwargs):
        try:
            return super(GuidView, self).get(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('spam_id')
                    )
                )
            )
