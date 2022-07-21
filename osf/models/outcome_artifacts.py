from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.identifiers import Identifier
from osf.utils.outcomes import ArtifactTypes, NoPIDError


'''
This module defines the OutcomeArtifact model and its custom manager.

OutcomeArtifacts are a through-table, providing some additional metadata on the relationship
between an Outcome and an external Identifier that stores materials or provides context
for the research effort described by the Outcome.
'''

class ArtifactManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().annotate(
            pid=models.F('identifier__value')
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
                raise NoPIDError('No PID with value {pid_value} found for PID type {pid_type}')

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

    title = models.TextField(null=False)
    description = models.TextField(null=False)

    objects = ArtifactManager()

    class Meta:
        unique_together = ('outcome', 'identifier', 'artifact_type')
        indexes = [
            models.Index(fields=['outcome', 'artifact_type'])
        ]
        ordering = ['artifact_type', 'title']
