from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.mixins import EditableFieldsMixin
from osf.utils.outcomes import ArtifactTypes, NoPIDError

class OutcomeManager(models.Manager):

    def for_registration(self, registration, identifier_type='doi', create=False, **kwargs):
        registration_identifier = registration.get_identifier(category=identifier_type)
        if not registration_identifier:
            raise NoPIDError(f'Provided registration has no PID of type {identifier_type}')

        primary_artifact = registration_identifier.outcomeartifact_set.filter(
            artifact_type=ArtifactTypes.PRIMARY.value
        ).order_by('-created').first()
        if primary_artifact:
            return primary_artifact.outcome
        elif not create:
            return None

        new_outcome = self.create(**kwargs)
        new_outcome.copy_editable_fields(registration, include_contributors=False)
        new_outcome.add_artifact(registration_identifier, ArtifactTypes.PRIMARY)
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
    # subjects (Subkects, M2M)

    # These overrid the fields inherited from EditableField Mixin
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

    def add_artifact(self, identifier, artifact_type):
        # After Django upgrade, this can simplify to
        # self.artifacts.add(identifier, through_defaults={'artifact_type': artifact_type})
        self.artifacts.through.objects.create(
            outcome=self, identifier=identifier, artifact_type=artifact_type
        )
