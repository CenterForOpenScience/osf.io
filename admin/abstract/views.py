from django.views.generic import FormView
from django.shortcuts import render
from django.views.defaults import page_not_found


class GuidFormView(FormView):
    form_class = None
    template_name = None
    object_type = None

    def get_guid_object(self):
        raise NotImplementedError

    def __init__(self):
        self.guid = None
        super(GuidFormView, self).__init__()

    def get(self, request, *args, **kwargs):
        try:
            return super(GuidFormView, self).get(request, args, kwargs)
        except AttributeError:
            return page_not_found(self.request)

    def get_context_data(self, **kwargs):
        self.guid = self.request.GET.get('guid', None)
        if self.guid is not None:
            try:
                guid_object = self.get_guid_object()
            except AttributeError:
                raise
        else:
            guid_object = None
        kwargs.setdefault('view', self)
        kwargs.setdefault('form', self.get_form())
        kwargs.setdefault('guid_object', guid_object)
        return kwargs

    def form_valid(self, form):
        self.guid = form.cleaned_data.get('guid').strip()
        return super(GuidFormView, self).form_valid(form)

    @property
    def success_url(self):
        raise NotImplementedError
