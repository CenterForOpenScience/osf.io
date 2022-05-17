from osf.models import RegistrationSchema
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, TemplateView, FormView
from admin.registration_schemas.forms import RegistrationSchemaForm
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy


class RegistrationSchemaDetailView(FormView, PermissionRequiredMixin, TemplateView):
    """
    """
    template_name = 'registration_schemas/registration_schema.html'
    permission_required = 'osf.view_registration_schema'
    raise_exception = True
    form_class = RegistrationSchemaForm

    def get_object(self):
        registration_schema = RegistrationSchema.objects.get(
            id=self.kwargs['registration_schema_id']
        )

        # django admin templates don't like attributes with underscores for some reason
        registration_schema.guid = registration_schema._id

        return registration_schema

    def get_context_data(self, *args, **kwargs):
        registration_schema = self.get_object()
        return super().get_context_data(
            **{
                'form': RegistrationSchemaForm(
                    data={
                        'name': registration_schema.name,
                        'schema_version': registration_schema.schema_version,
                        'registration_schema': self.get_object()
                    },
                ),
                'registration_schema': registration_schema,
            }
        )

    def form_valid(self, form):
        registration_schema = self.get_object()
        print(form.data)
        registration_schema.save()

        return super().form_valid()

    def post(self, request, *args, **kwargs):
        print("PSOF")
        return super().post(request, *args, **kwargs)

        return redirect(self.get_success_url())

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('registration_schemas:detail', kwargs={'registration_schema_id': self.get_object().id})




class RegistrationSchemaListView(PermissionRequiredMixin, ListView):
    """
    """
    template_name = 'registration_schemas/registration_schema_list.html'
    permission_required = 'osf.view_registration_schema'
    raise_exception = True

    def get_queryset(self):
        return RegistrationSchema.objects.all()

    def get_context_data(self, *, object_list=None, **kwargs):
        return {'registration_schemas': self.get_queryset()}

