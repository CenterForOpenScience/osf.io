from django.db import models, IntegrityError, transaction
from django.utils import timezone

from osf.exceptions import (
    CannotFinalizeArtifactError,
    IdentifierHasReferencesError,
    InvalidPIDError,
    NoPIDError,
    UnsupportedArtifactTypeError,
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
        blank=True,
        on_delete=models.SET_NULL,
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
        indexes = [
            models.Index(fields=['artifact_type', 'outcome'])
        ]
        ordering = ['artifact_type', 'title']

    def update(
        self,
        new_description=None,
        new_artifact_type=None,
        new_pid_value=None,
        pid_type='doi',
        api_request=None
    ):
        log_params = {}
        if new_description is not None:
            self.description = new_description

        if new_artifact_type is not None:
            if new_artifact_type == ArtifactTypes.UNDEFINED != self.artifact_type:
                raise UnsupportedArtifactTypeError
            self.artifact_type = new_artifact_type

        if new_pid_value is not None:
            log_params = {
                'obsolete_identifier': self.identifier.value if self.identifier else '',
                'new_identifier': new_pid_value
            }
            self._update_identifier(new_pid_value, pid_type, api_request)

        if self.finalized:
            self.outcome.artifact_updated(
                artifact=self,
                action=OutcomeActions.UPDATE if new_pid_value is not None else None,
                api_request=api_request,
                **log_params,
            )

    @transaction.atomic
    def _update_identifier(self, new_pid_value, pid_type='doi', api_request=None):
        '''Changes the linked Identifer to one matching the new pid_value and handles callbacks.

        If `finalized` is True, will also log the change on the parent Outcome if invoked via API.
        Will attempt to delete the previous identifier to avoid orphaned entries.

        Parameters:
        new_pid_value: The string value of the new PID
        pid_type (str): The string "type" of the new PID (for now, only "doi" is supported)
        api_request: The api_request data from the API call that initiated the change.
        '''
        if not new_pid_value:
            raise NoPIDError('Cannot assign an empty PID value')

        new_identifier, created = Identifier.objects.get_or_create(
            value=new_pid_value, category=pid_type
        )
        if created:
            try:
                new_identifier.validate_identifier_value()
            except InvalidPIDError as e:
                new_identifier.delete()
                raise e

        previous_identifier = self.identifier
        self.identifier = new_identifier
        self.save()
        if previous_identifier:
            try:
                previous_identifier.delete()
            except IdentifierHasReferencesError:
                pass

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

        if OutcomeArtifact.objects.filter(
            outcome=self.outcome,
            identifier=self.identifier,
            artifact_type=self.artifact_type,
            finalized=True,
            deleted__isnull=True,
        ).exists():
            raise IntegrityError(
                f'Finalized OutcomeArtifact with PID {self.identifier.value} and artifact_type '
                f'{self.artifact_type} already exists on Outcome with ID [{self.outcome._id}].'
            )

        self.finalized = True
        self.save()

        if api_request:
            self.outcome.artifact_updated(
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
                self.outcome.artifact_updated(
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
