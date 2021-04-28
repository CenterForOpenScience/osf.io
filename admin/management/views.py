from django.views.generic import TemplateView, View, FormView
from django.contrib import messages
from osf.management.commands.manage_switch_flags import manage_waffle
from osf.management.commands.update_registration_schemas import (
    update_registration_schemas,
)
from osf.management.commands.archive_registrations_on_IA import (
    archive_registrations_on_IA,
)
from osf.management.commands.populate_internet_archives_collections import (
    populate_internet_archives_collections,
)
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from admin.users.forms import ArchiveRegistrationWithPigeonForm
from website import settings


class ManagementCommands(TemplateView):
    """Basic form to trigger various management commands"""

    template_name = "management/commands.html"
    object_type = "management"


class WaffleFlag(View):
    def post(self, request, *args, **kwargs):
        manage_waffle()
        messages.success(request, "Waffle flags have been successfully updated.")
        return redirect(reverse("management:commands"))


class UpdateRegistrationSchemas(View):
    def post(self, request, *args, **kwargs):
        update_registration_schemas()
        messages.success(
            request, "Registration schemas have been successfully updated."
        )
        return redirect(reverse("management:commands"))


class SendToPigeon(FormView):

    form_class = ArchiveRegistrationWithPigeonForm
    raise_exception = True

    def form_valid(self, form):
        guids = form.cleaned_data["guid_to_archive"]
        if guids:
            guids = [
                guid.strip() for guid in form.cleaned_data["guid_to_archive"].split(",")
            ]
            archive_registrations_on_IA(guids=guids)
            messages.success(self.request, f'{" ,".join(guids)} has begun archiving.')
        else:
            archive_registrations_on_IA()
            messages.success(self.request, "Registrations have begun archiving.")

        return super().form_valid(form)

    def get_success_url(self, *args, **kwargs):
        return reverse("management:commands")


class CreateIASubcollections(View):
    def post(self, request, *args, **kwargs):
        populate_internet_archives_collections(settings.IA_ID_VERSION)
        messages.success(
            request,
            f"Subcollections with ids of {settings.IA_ID_VERSION} are being created",
        )
        return redirect(reverse("management:commands"))
