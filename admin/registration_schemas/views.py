import csv
import codecs
from osf.models import RegistrationSchema
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, TemplateView, FormView, DeleteView
from admin.registration_schemas.forms import RegistrationSchemaCreateForm, RegistrationSchemaEditForm
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.db.models import Max
from django.http import HttpResponseRedirect

from osf.utils.migrations import map_schemas_to_schemablocks


class RegistrationSchemaDetailView(FormView, PermissionRequiredMixin, TemplateView):
    """
    Allows authorized users to view and edit some attributes of a Registration Schema.
    """
    template_name = 'registration_schemas/registration_schema.html'
    permission_required = 'osf.view_registration_schema'
    raise_exception = True
    form_class = RegistrationSchemaEditForm

    def get_object(self):
        return RegistrationSchema.objects.get(
            id=self.kwargs['registration_schema_id']
        )

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
    Allows authorized users to create a Registration Schema.
    """
    template_name = 'registration_schemas/registration_schema_create.html'
    permission_required = 'osf.change_registrationschema'
    raise_exception = True
    form_class = RegistrationSchemaCreateForm

    def form_valid(self, form):
        latest_version = RegistrationSchema.objects.filter(
            name=form.data['name']
        ).aggregate(latest_version=Max('schema_version'))['latest_version'] or 0

        blocks = self.csv_to_blocks(form.files['schema'])
        registration_schema = RegistrationSchema.objects.create(
            name=form.data['name'],
            schema={
                'atomicSchema': True,
                'version': latest_version + 1,
                'blocks': blocks,
            },
            active=False,
            visible=False,
            schema_version=latest_version + 1,
        )
        map_schemas_to_schemablocks()

        self.success_url = reverse_lazy(
            'registration_schemas:detail',
            kwargs={
                'registration_schema_id': registration_schema.id,
            }
        )
        messages.success(
            self.request,
            f'{registration_schema.name} ({registration_schema.schema_version}) created with '
            f'{registration_schema.schema_blocks.count()} blocks.'
        )

        return super().form_valid(form)

    def csv_to_blocks(self, file):
        rows = [row for row in csv.DictReader(codecs.iterdecode(file.file, 'utf-8-sig'), delimiter=',')]

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


class RegistrationSchemaDeleteView(DeleteView, PermissionRequiredMixin):
    """
    Allows authorized users to delete a Registration Schema.
    """
    permission_required = 'osf.change_registrationschema'
    raise_exception = True
    form_class = RegistrationSchemaCreateForm
    success_url = reverse_lazy('registration_schemas:list')
    model = RegistrationSchema

    def get_object(self, queryset=None):
        return RegistrationSchema.objects.get(id=self.kwargs['registration_schema_id'])

    def delete(self, request, *args, **kwargs):
        providers = self.get_object().providers.all()
        if providers:
            messages.warning(
                request,
                f'Schema could not be deleted because it\'s still associated with {",".join(providers.values_list("name", flat=True))}')
            return HttpResponseRedirect(self.success_url)

        ret = super().delete(request, *args, **kwargs)
        messages.success(request, 'Schema deleted!')
        return ret


class RegistrationSchemaListView(PermissionRequiredMixin, ListView):
    """
    Allows authorized users to view all Registration Schema.
    """
    template_name = 'registration_schemas/registration_schema_list.html'
    permission_required = 'osf.view_registration_schema'
    raise_exception = True

    def get_queryset(self):
        return RegistrationSchema.objects.all().order_by('name', 'schema_version')

    def get_context_data(self, *, object_list=None, **kwargs):
        return {'registration_schemas': self.get_queryset()}
