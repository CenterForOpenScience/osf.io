from django.db import models

from osf.exceptions import IdentifierHasReferencesError
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.identifiers import Identifier
from osf.utils import outcomes as outcome_utils
from osf.utils.fields import NonNaiveDateTimeField


'''
This module defines the OutcomeArtifact model and its custom manager.

OutcomeArtifacts are a through-table, providing some additional metadata on the relationship
between an Outcome and an external Identifier that stores materials or provides context
for the research effort described by the Outcome.
'''


ArtifactTypes = outcome_utils.ArtifactTypes


class ArtifactManager(models.Manager):

    def get_queryset(self):
        base_queryset = super().get_queryset().select_related('identifier')
        return base_queryset.annotate(
            pid=models.F('identifier__value'),
            primary_resource_guid=outcome_utils.make_primary_resource_guid_annotation(base_queryset)
        )

    def create_for_identifier_value(
        self, outcome, pid_value, pid_type='doi', create_identifier=False, **kwargs
    ):
        if create_identifier:
            identifier, _ = Identifier.objects.get_or_create(
                value=pid_value, category=pid_type
            )
        else:
            try:
                identifier = Identifier.objects.get(
                    value=pid_value, category=pid_type
                )
            except Identifier.DoesNotExist:
                raise outcome_utils.NoPIDError(
                    'No PID with value {pid_value} found for PID type {pid_type}'
                )

        return self.create(outcome=outcome, identifier=identifier, **kwargs)

    def for_registration(self, registration, identifier_type='doi'):
        registration_identifier = registration.get_identifier(identifier_type)
        artifact_qs = self.get_queryset()
        return artifact_qs.annotate(
            primary_outcome=models.Subquery(
                artifact_qs.filter(
                    identifier=registration_identifier,
                    artifact_type=ArtifactTypes.PRIMARY
                ).values('outcome_id')[:1],
                output_field=models.IntegerField()
            )
        ).filter(
            outcome_id=models.F('primary_outcome')
        ).exclude(
            identifier=registration_identifier
        )


class OutcomeArtifact(ObjectIDMixin, BaseModel):
    '''OutcomeArtifact is a through table that connects an Outcomes with Identifiers
    while providing some additional, useful metadata'''

    # The following fields are inherited from ObjectIdMixin
    # _id (CharField)

    # The following fields are inherited from BaseModel
    # created (DateTimeField)
    # modified (DateTimeField)

    outcome = models.ForeignKey(
        'osf.outcome',
        on_delete=models.CASCADE,
        related_name='artifact_metadata'
    )
    identifier = models.ForeignKey(
        'osf.identifier',
        null=True,
        on_delete=models.CASCADE,
        related_name='artifact_metadata'
    )

    artifact_type = models.IntegerField(
        null=False,
        choices=ArtifactTypes.choices(),
        default=ArtifactTypes.UNDEFINED,
    )

    title = models.TextField(null=False, blank=True)
    description = models.TextField(null=False, blank=True)
    finalized = models.BooleanField(default=False)
    deleted = NonNaiveDateTimeField(null=True, blank=True)

    objects = ArtifactManager()

    class Meta:
        unique_together = ('outcome', 'identifier', 'artifact_type')
        indexes = [
            models.Index(fields=['outcome', 'artifact_type'])
        ]
        ordering = ['artifact_type', 'title']

    def update_identifier(self, new_pid_value, pid_type='doi'):
        previous_identifier = self.identifier
        self.identifier, _ = Identifier.objects.get_or_create(
            value=new_pid_value, category=pid_type
        )
        self.save()
        if previous_identifier:
            try:
                previous_identifier.delete()
            except IdentifierHasReferencesError:
                pass

    def delete(self):
        if self.finalized:
            raise RuntimeError
        identifier = self.identifier
        super().delete()

        try:
            identifier.delete()
        except IdentifierHasReferencesError:
            pass
