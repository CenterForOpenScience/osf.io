from django.views.generic import TemplateView, View, FormView
from django.contrib import messages
from osf.management.commands.archive_registrations_on_IA import (
    archive_registrations_on_IA,
)
from osf.management.commands.populate_internet_archives_collections import (
    populate_internet_archives_collections,
)
from osf.management.commands.check_ia_metadata import (
    check_ia_metadata,
    IAMetadataError,
)
from osf.management.commands.sync_ia_metadata import (
    sync_ia_metadata,
)
from django.urls import reverse
from django.shortcuts import redirect
from admin.base.forms import ArchiveRegistrationWithPigeonForm
from website import settings
from django.contrib.auth.mixins import PermissionRequiredMixin


class InternetArchiveView(TemplateView, PermissionRequiredMixin):
    """Basic form to trigger various management commands"""

    template_name = "internet_archive/internet_archive.html"
    permission_required = "osf.change_node"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ia_collection"] = settings.IA_ROOT_COLLECTION
        context["ia_id_version"] = settings.ID_VERSION
        context["osf_pigeon_url"] = settings.OSF_PIGEON_URL
        return context


class SendToPigeon(FormView, PermissionRequiredMixin):
    form_class = ArchiveRegistrationWithPigeonForm
    raise_exception = True
    permission_required = "osf.change_node"

    def form_valid(self, form):
        guids = form.cleaned_data["guid_to_archive"]
        guids = [guid.strip() for guid in guids.split(",") if guid]
        archive_registrations_on_IA(guids=guids)
        messages.success(
            self.request,
            f'{" ,".join(guids) if guids else "the job"} has begun archiving.',
        )

        return super().form_valid(form)

    def get_success_url(self, *args, **kwargs):
        return reverse("internet_archive:internet_archive")


class CreateIASubcollections(View, PermissionRequiredMixin):
    def post(self, request, *args, **kwargs):
        populate_internet_archives_collections(settings.ID_VERSION)
        messages.success(
            request,
            f"Subcollections with ids of {settings.ID_VERSION} are being created",
        )
        return redirect(reverse("internet_archive:internet_archive"))


class CheckIAMetadata(FormView, PermissionRequiredMixin):
    form_class = ArchiveRegistrationWithPigeonForm
    raise_exception = True
    permission_required = "osf.change_node"

    def form_valid(self, form):
        guids = form.cleaned_data["guid_to_archive"]
        guids = [guid.strip() for guid in guids.split(",") if guid]
        try:
            check_ia_metadata(guids=guids)
            messages.success(self.request, "All IA items are synced")
        except IAMetadataError as e:
            messages.error(self.request, e.message)
            if e.fields:
                for ai_url, data in e.fields.items():
                    messages.error(
                        self.request, f'{ai_url}: {", ".join(data["fields"])}'
                    )

        return super().form_valid(form)

    def get_success_url(self, *args, **kwargs):
        return reverse("internet_archive:internet_archive")


class SyncIAMetadata(FormView, PermissionRequiredMixin):
    form_class = ArchiveRegistrationWithPigeonForm
    raise_exception = True
    permission_required = "osf.change_node"

    def form_valid(self, form):
        guids = form.cleaned_data["guid_to_archive"]
        guids = [guid.strip() for guid in guids.split(",") if guid]
        sync_ia_metadata(guids=guids)
        messages.success(self.request, f'{", ".join(guids)} match IA items.')
        return super().form_valid(form)

    def get_success_url(self, *args, **kwargs):
        return reverse("internet_archive:internet_archive")
