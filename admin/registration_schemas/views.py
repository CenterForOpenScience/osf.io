import csv
import codecs
from osf.models import RegistrationSchema
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, TemplateView, FormView
from admin.registration_schemas.forms import RegistrationSchemaCreateForm, RegistrationSchemaEditForm
from django.contrib import messages
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy
from osf.utils.migrations import map_schemas_to_schemablocks

class RegistrationSchemaDetailView(FormView, PermissionRequiredMixin, TemplateView):
    """
    """
    template_name = 'registration_schemas/registration_schema.html'
    permission_required = 'osf.view_registration_schema'
    raise_exception = True
    form_class = RegistrationSchemaEditForm

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
                'form': RegistrationSchemaEditForm(
                    data={
                        'active': registration_schema.active,
                        'visible': registration_schema.visible,
                    },
                ),
                'registration_schema': registration_schema,
            },
        )

    def form_valid(self, form):
        registration_schema = self.get_object()
        registration_schema.active = bool(form.data.get('active', False))
        registration_schema.visible = bool(form.data.get('visible', False))
        registration_schema.save()
        return super().form_valid(form)


    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('registration_schemas:detail', kwargs={'registration_schema_id': self.get_object().id})



class RegistrationSchemaCreateView(FormView, PermissionRequiredMixin):
    """
    """
    template_name = 'registration_schemas/registration_schema_create.html'
    permission_required = 'osf.change_registrationschema'
    raise_exception = True
    form_class = RegistrationSchemaCreateForm

    def form_valid(self, form):
        latest_version = RegistrationSchema.objects.get_latest_version(form.data['name']) or 1

        blocks = self.csv_to_blocks(form.files['schema'])
        registration_schema = RegistrationSchema.objects.create(
            name=form.data['name'],
            schema={
                "atomicSchema": True,
                "version": latest_version + 1,
                "blocks": blocks,
            },
            active=False,
            visible=False,
            schema_version=latest_version + 1
        )
        map_schemas_to_schemablocks()

        self.object = registration_schema
        messages.success(
            self.request,
            f'{registration_schema.name} ({registration_schema.schema_version}) created with '
            f'{registration_schema.schema_blocks.count()} blocks.'
        )

        return super().form_valid(form)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('registration_schemas:detail',  kwargs={'registration_schema_id': self.object.id})

    def csv_to_blocks(self, file):
        rows = [row for row in csv.DictReader(codecs.iterdecode(file.file, 'utf-8-sig'), delimiter=",")]

        blocks = []
        for row in rows:
            data = {}
            for key, value in list(row.items()):
                if value is not '' and not key.startswith('NOEX'):
                    if value == 'FALSE':
                        data.update({key: False})
                    elif value == 'TRUE':
                        data.update({key: True})
                    else:
                        data.update({key: value})
            blocks.append(data)

        return blocks


class RegistrationSchemaListView(PermissionRequiredMixin, ListView):
    """
    """
    template_name = 'registration_schemas/registration_schema_list.html'
    permission_required = 'osf.view_registration_schema'
    raise_exception = True

    def get_queryset(self):
        return RegistrationSchema.objects.all().order_by('name')

    def get_context_data(self, *, object_list=None, **kwargs):
        return {'registration_schemas': self.get_queryset()}

