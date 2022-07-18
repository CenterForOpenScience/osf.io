from django.db import models
from django.utils.functional import cached_property

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.mixins import EditableFieldsMixin
from osf.utils.outcomes import ArtifactTypes, NoPIDError

'''
This module defines the Outcome model and its custom manager.

Outcomes serve as a way to collect metadata about a research effort and to aggregate Identifiers
used to share data or provide context for a that research effort, along with some additional metadata
stored in the OutcomeArtifact through table.
'''


class OutcomeManager(models.Manager):

    def for_registration(self, registration, identifier_type='doi', create=False, **kwargs):
        registration_identifier = registration.get_identifier(category=identifier_type)
        if not registration_identifier:
            raise NoPIDError(f'Provided registration has no PID of type {identifier_type}')

        primary_artifact = registration_identifier.artifact_metadata.filter(
            artifact_type=ArtifactTypes.PRIMARY.value
        ).order_by('-created').first()
        if primary_artifact:
            return primary_artifact.outcome
        elif not create:
            return None

        new_outcome = self.create(**kwargs)
        new_outcome.copy_editable_fields(registration, include_contributors=False)
        new_outcome.artifact_metadata.create(
            identifier=registration_identifier,
            artifact_type=ArtifactTypes.PRIMARY
        )
        return new_outcome


class Outcome(ObjectIDMixin, EditableFieldsMixin, BaseModel):
    # The following fields are inherited from ObjectIdMixin
    # _id (CharField)

    # The following fields are inherited from BaseModel
    # created (DateTimeField)
    # modified (DateTimeField)

    # The following fields inherited from EditableFieldsMixin:
    # title (TextField)
    # description (TextField)
    # category (CharField)
    # tags (Tags, M2M)
    # subjects (Subjects, M2M)

    # These override the fields inherited from EditableField Mixin
    # This is required to avoid collisions with the related_name
    affiliated_institutions = models.ManyToManyField('Institution', related_name='outcomes')
    node_license = models.ForeignKey(
        'NodeLicenseRecord',
        related_name='outcomes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    artifacts = models.ManyToManyField('osf.Identifier', through='osf.OutcomeArtifact')

    objects = OutcomeManager()

    @cached_property
    def primary_osf_resource(self):
        return self.artifact_metadata.get(artifact_type=ArtifactTypes.PRIMARY).identifier.referent

    def add_artifact_by_pid(self, pid, artifact_type, pid_type='doi', create_identifier=False):
        return self.artifacts.through.objects.create_for_identifier_value(
            outcome=self,
            pid_value=pid,
            pid_type=pid_type,
            artifact_type=artifact_type,
            create_identifier=create_identifier
        )
