from django.db import models
from django.utils import timezone

from osf.exceptions import (
    CannotFinalizeArtifactError,
    IdentifierHasReferencesError,
    NoPIDError
)
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
OutcomeActions = outcome_utils.OutcomeActions


class ArtifactManager(models.Manager):

    def get_queryset(self):
        '''Overrides default `get_queryset` behavior to add custom logic.

        Automatically annotates the `pid` from any linked identifier and the
        GUID of the primary resource for the parent artifact.

        Automatically filters out deleted entries
        '''
        base_queryset = super().get_queryset().select_related('identifier')
        return base_queryset.annotate(
            pid=models.F('identifier__value'),
            primary_resource_guid=outcome_utils.make_primary_resource_guid_annotation(base_queryset)
        )

    def for_registration(self, registration, identifier_type='doi'):
        '''Retrieves all OutcomeArtifacts sharing an Outcome, given the Primary Registration.'''
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

    def update_identifier(self, new_pid_value, pid_type='doi', api_request=None):
        '''Changes the linked Identifer to one matching the new pid_value and handles callbacks.

        If `finalized` is True, will also log the change on the parent Outcome if invoked via API.
        Will attempt to delete the previous identifier to avoid orphaned entries.

        Parameters:
        new_pid_value: The string value of the new PID
        pid_type (str): The string "type" of the new PID (for now, only "doi" is supported)
        api_request: The api_request data from the API call that initiated the change.
        '''
        if not new_pid_value:
            raise NoPIDError(f'Cannot assign an empty PID to OutcomeArtifact with ID {self._id}')

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

        if self.finalized and api_request:
            self.outcome.log_artifact_change(
                action=OutcomeActions.UPDATE,
                artifact=self,
                api_request=api_request,
                obsolete_identifier=previous_identifier.value if previous_identifier else None,
                new_identifier=new_pid_value
            )

    def finalize(self, api_request=None):
        '''Sets `finalized` to True and handles callbacks.

        Logs the change on the parent Outcome if invoked via the API.

        Parameters:
        api_request: The api_request data from the API call that initiated the change.
        '''
        incomplete_fields = []
        if not (self.identifier and self.identifier.value):
            incomplete_fields.append('identifier__value')
        if not self.artifact_type:
            incomplete_fields.append('artifact_type')
        if incomplete_fields:
            raise CannotFinalizeArtifactError(self, incomplete_fields)

        self.finalized = True
        self.save()

        if api_request:
            self.outcome.log_artifact_change(
                action=OutcomeActions.ADD,
                artifact=self,
                api_request=api_request,
                new_identifier=self.identifier.value
            )

    def delete(self, api_request=None, **kwargs):
        '''Intercept `delete` behavior on the model instance and handles callbacks.

        Deletes from database if not `finalized` otherwise sets the `deleted` timestamp.
        Logs the change on the parent Outcome if invoked via the API.
        Attempts to delete the linked Identifier to avoid orphaned entries.

        Parameters:
        api_request: The api_request data from the API call that initiated the change.
        '''
        identifier = self.identifier
        if self.finalized:
            if api_request:
                self.outcome.log_artifact_change(
                    action=OutcomeActions.REMOVE,
                    artifact=self,
                    api_request=api_request,
                    obsolete_identifier=identifier.value
                )
            self.deleted = timezone.now()
            self.save()
        else:
            super().delete(**kwargs)

        try:
            identifier.delete()
        except IdentifierHasReferencesError:
            pass
