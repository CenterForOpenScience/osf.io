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
        self.guid = request.GET.get('guid', None)
        if self.guid is not None:
            try:
                guid_object = self.get_guid_object()
            except AttributeError:
                error_str = u'{} ({}) not found.'.format(
                    self.object_type, self.guid)
                return page_not_found(request, AttributeError(error_str))
        else:
            guid_object = None
        form = self.get_form()
        context = {
            'guid_object': guid_object,
            'form': form,
        }
        return render(request, self.template_name, context)

    def form_valid(self, form):
        self.guid = form.cleaned_data.get('guid').strip()
        return super(GuidFormView, self).form_valid(form)

    def get_initial(self):
        self.initial = {
            'guid': self.guid,
        }
        return super(GuidFormView, self).get_initial()

    @property
    def success_url(self):
        raise NotImplementedError
