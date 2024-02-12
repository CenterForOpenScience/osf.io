from unittest import mock

import pytest
from django.db import IntegrityError
from django.utils import timezone

from osf.exceptions import (
    CannotFinalizeArtifactError,
    InvalidPIDError,
    InvalidPIDFormatError,
    IsPrimaryArtifactPIDError,
    NoPIDError,
    NoSuchPIDError,
    UnsupportedArtifactTypeError
)
from osf.models import Identifier, Outcome, OutcomeArtifact
from osf.utils.outcomes import ArtifactTypes
from osf_tests.factories import ProjectFactory, RegistrationFactory


TEST_REGISTRATION_DOI = 'SOME_REGISTRATION_DOI'
TEST_PROJECT_DOI = 'SOME_PROJECT_DOI'
TEST_EXTERNAL_DOI = 'SOME_EXTERNAL_DOI'


@pytest.fixture
def registration():
    return RegistrationFactory()

@pytest.fixture
def registration_doi(registration):
    return Identifier.objects.create(
        referent=registration,
        value=TEST_REGISTRATION_DOI,
        category='doi'
    )

@pytest.fixture
def outcome(registration_doi):
    outcome = Outcome.objects.create()
    OutcomeArtifact.objects.create(
        outcome=outcome,
        identifier=registration_doi,
        artifact_type=ArtifactTypes.PRIMARY
    )
    return outcome


@pytest.mark.django_db
class TestOutcomes:

    def test_outcome_for_registration__get__exists(self, outcome, registration):
        stored_outcome = Outcome.objects.for_registration(registration, create=False)
        assert stored_outcome == outcome

    def test_outcome_for_registration__get__none_exists(self, registration, registration_doi):
        assert not Outcome.objects.for_registration(registration, create=False)

    def test_outcome_for_registration__get__no_registration_identifier(self, registration):
        with pytest.raises(NoPIDError):
            Outcome.objects.for_registration(registration)

    def test_outcome_for_registration__create(self, registration, registration_doi):
        assert not Outcome.objects.exists()
        Outcome.objects.for_registration(registration, create=True)
        assert Outcome.objects.exists()

    def test_outcome_for_registration__create__no_identifier(self, registration):
        with pytest.raises(NoPIDError):
            Outcome.objects.for_registration(registration, create=True)

    def test_outcome_for_registration__create_creates_primary_artifact(
        self, registration, registration_doi
    ):
        outcome = Outcome.objects.for_registration(registration, create=True)

        assert outcome.artifacts.count() == 1
        primary_artifact = outcome.artifacts.through.objects.get()
        assert primary_artifact.identifier == registration_doi
        assert primary_artifact.pid == registration_doi.value
        assert primary_artifact.artifact_type == ArtifactTypes.PRIMARY
        assert primary_artifact.primary_resource_guid == registration._id

    def test_outcome_for_registration__create_copies_metadata(self, registration, registration_doi):
        outcome = Outcome.objects.for_registration(registration, create=True)
        assert outcome.title == registration.title
        assert outcome.description == registration.description
        assert outcome.category == registration.category

    def test_primary_osf_resource(self, outcome, registration):
        assert outcome.primary_osf_resource == registration


@pytest.mark.django_db
@mock.patch('osf.utils.identifiers.PID_VALIDATION_ENABLED', False)
class TestOutcomeArtifact:

    @pytest.fixture
    def outcome(self, registration_doi):
        outcome = Outcome.objects.create()
        OutcomeArtifact.objects.create(
            outcome=outcome,
            identifier=registration_doi,
            artifact_type=ArtifactTypes.PRIMARY
        )
        return outcome

    @pytest.fixture
    def project_doi(self):
        project = ProjectFactory()
        return Identifier.objects.create(
            referent=project,
            value=TEST_PROJECT_DOI,
            category='doi'
        )

    @pytest.fixture
    def external_doi(self):
        return Identifier.objects.create(
            value=TEST_EXTERNAL_DOI,
            category='doi'
        )

    def test_get_artifacts_for_registration(self, outcome, registration, project_doi, external_doi):
        assert not OutcomeArtifact.objects.for_registration(registration).exists()

        project_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.MATERIALS
        )
        external_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.SUPPLEMENTS
        )

        # Add another Artifact for one of the identifiers to make sure it doesn't get picked up, too
        bogus_outcome = Outcome.objects.create()
        bogus_outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.ANALYTIC_CODE
        )

        registration_artifacts = OutcomeArtifact.objects.for_registration(registration)
        # Registration artifact should not appear in the list
        assert registration_artifacts.count() == 2

        retrieved_project_artifact = registration_artifacts.get(identifier=project_doi)
        assert retrieved_project_artifact == project_artifact
        assert retrieved_project_artifact.pid == TEST_PROJECT_DOI
        assert retrieved_project_artifact.primary_resource_guid == registration._id

        retrieved_external_artifact = registration_artifacts.get(identifier=external_doi)
        assert retrieved_external_artifact == external_artifact
        assert retrieved_external_artifact.pid == TEST_EXTERNAL_DOI
        assert retrieved_external_artifact.primary_resource_guid == registration._id

    def test_update__new_artifact_type__undefined_raises_if_not_undefined(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(identifier=project_doi, artifact_type=ArtifactTypes.DATA)

        with pytest.raises(UnsupportedArtifactTypeError):
            test_artifact.update(new_artifact_type=ArtifactTypes.UNDEFINED)

    def test_update__new_artifact_type__undefined_allowed_if_already_undefined(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(identifier=project_doi)

        test_artifact.update(new_artifact_type=ArtifactTypes.UNDEFINED)
        assert test_artifact.artifact_type == ArtifactTypes.UNDEFINED

    def test_update__new_pid__get_existing_identifier(self, outcome, project_doi, external_doi):
        test_artifact = outcome.artifact_metadata.create(artifact_type=ArtifactTypes.DATA)
        test_artifact.update(new_pid_value=TEST_PROJECT_DOI)
        assert test_artifact.identifier == project_doi

    def test_update__new_pid__create_new_identifier(self, outcome, project_doi):
        assert not Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

        test_artifact = outcome.artifact_metadata.create(artifact_type=ArtifactTypes.DATA)
        test_artifact.update(new_pid_value=TEST_EXTERNAL_DOI)

        assert test_artifact.identifier.value == TEST_EXTERNAL_DOI
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    def test_update__new_pid__deletes_previous_identifier_if_unreferenced(self, outcome, project_doi, external_doi):
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()
        test_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.DATA
        )
        assert test_artifact.identifier != project_doi

        test_artifact.update(new_pid_value=project_doi.value)
        assert test_artifact.identifier == project_doi
        assert not Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    def test_update__new_pid__keeps_previous_identifier_if_osf_referent_exists(self, outcome, project_doi):
        assert Identifier.objects.filter(value=TEST_PROJECT_DOI).exists()
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        test_artifact.update(new_pid_value=TEST_EXTERNAL_DOI)
        assert test_artifact.identifier != project_doi
        assert Identifier.objects.filter(value=TEST_PROJECT_DOI).exists()

    def test_update__new_pid__keeps_previous_identifier_if_part_of_other_outcomes(
        self, outcome, project_doi, external_doi
    ):
        test_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.DATA
        )
        alternate_outcome = Outcome.objects.create()
        alternate_outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.ANALYTIC_CODE
        )

        test_artifact.update(new_pid_value=project_doi.value)
        assert test_artifact.identifier == project_doi
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    def test_update__new_pid__no_change_if_same_pid(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        test_artifact.update(new_pid_value=project_doi.value)
        assert test_artifact.identifier == project_doi

    def test_update__new_pid__raises_if_empty_pid(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        with pytest.raises(NoPIDError):
            test_artifact.update(new_pid_value='')

    def test_update__new_pid__primary_pid_cannot_be_reused(self, outcome, registration_doi):
        test_artifact = outcome.artifact_metadata.create(finalized=False)
        with pytest.raises(IsPrimaryArtifactPIDError):
            test_artifact.update(new_pid_value=registration_doi.value)

    @pytest.mark.parametrize('validation_error', [InvalidPIDError, InvalidPIDFormatError, NoSuchPIDError])
    def test_update__new_pid__reverts_and_reraises_on_invalid_pid(self, outcome, project_doi, validation_error):
        test_artifact = outcome.artifact_metadata.create(identifier=project_doi)

        invalid_identifier = 'apparently invalid'
        with mock.patch.object(Identifier, 'validate_identifier_value') as mock_validate:
            mock_validate.side_effect = validation_error('', '')
            with pytest.raises(validation_error):
                test_artifact.update(new_pid_value=invalid_identifier)

        assert test_artifact.identifier == project_doi
        assert not Identifier.objects.filter(value=invalid_identifier).exists()

    @pytest.mark.parametrize('protocol', ['http://', 'https://', 'ftp://', ''])
    @pytest.mark.parametrize('domain', ['doi.org/', ''])
    def test_update__new_pid__normalizes_pid_value(self, outcome, project_doi, protocol, domain):
        test_artifact = outcome.artifact_metadata.create(identifier=project_doi)
        base_pid_value = 'new_pid'
        provided_pid_value = f'{protocol}{domain}{base_pid_value}'

        test_artifact.update(new_pid_value=provided_pid_value)
        assert test_artifact.identifier.value == base_pid_value

    def test_update__enforces_uniqueness_if_finalized(self, outcome, project_doi):
        outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        # Can create the new artifact, but fails on `finalize`
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.MATERIALS,
        )

        test_artifact.finalize()  # Can finalize with same DOI but different artifact_type
        with pytest.raises(IntegrityError):  # Raise when set to a duplicate artifact_type
            test_artifact.update(new_artifact_type=ArtifactTypes.DATA)

    def test_update__enforces_uniquenss_if_finalized__nonfinal_duplicate_okay(self, outcome, project_doi):
        nonfinal_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=False
        )
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.MATERIALS, finalized=True
        )

        test_artifact.update(new_artifact_type=nonfinal_artifact.artifact_type)
        assert test_artifact.artifact_type == nonfinal_artifact.artifact_type
        assert test_artifact.identifier == nonfinal_artifact.identifier

    def test_update__enforces_uniquenss_if_finalized__deleted_duplicate_okay(self, outcome, project_doi):
        deleted_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True, deleted=timezone.now()
        )
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.MATERIALS, finalized=True
        )

        test_artifact.update(new_artifact_type=deleted_artifact.artifact_type)
        assert test_artifact.artifact_type == deleted_artifact.artifact_type
        assert test_artifact.identifier == deleted_artifact.identifier

    def test_finalize__raises__missing_identifier(self, outcome):
        test_artifact = outcome.artifact_metadata.create(artifact_type=ArtifactTypes.DATA)

        with pytest.raises(CannotFinalizeArtifactError) as caught:
            test_artifact.finalize()
        assert caught.value.incomplete_fields == ['identifier__value']

    def test_finalize__raises__missing_identifier_value(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )
        project_doi.value = ''
        project_doi.save()

        with pytest.raises(CannotFinalizeArtifactError) as caught:
            test_artifact.finalize()
        assert caught.value.incomplete_fields == ['identifier__value']

    def test_finalize__raises__missing_artifact_type(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(identifier=project_doi)

        with pytest.raises(CannotFinalizeArtifactError) as caught:
            test_artifact.finalize()
        assert caught.value.incomplete_fields == ['artifact_type']

    def test_finalize__raises__missing_both(self, outcome):
        test_artifact = outcome.artifact_metadata.create()

        with pytest.raises(CannotFinalizeArtifactError) as caught:
            test_artifact.finalize()
        assert caught.value.incomplete_fields == ['identifier__value', 'artifact_type']

    def test_finalize__enforces_uniqueness(self, outcome, project_doi):
        outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        # Can create the new artifact, but fails on `finalize`
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        with pytest.raises(IntegrityError):
            test_artifact.finalize()

    def test_finalize__enforces_uniquenss__deleted_entry_okay(self, outcome, project_doi):
        outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True, deleted=timezone.now()
        )
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        test_artifact.finalize()
        assert test_artifact.finalized

    def test_delete_artifact__deletes_from_db_if_not_finalized(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=False
        )

        test_artifact.delete()
        assert not OutcomeArtifact.objects.filter(id=test_artifact.id).exists()

    def test_delete_artifact__sets_deleted_if_finalized(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        assert not test_artifact.deleted

        test_artifact.delete()
        assert test_artifact.deleted
        assert OutcomeArtifact.objects.filter(id=test_artifact.id).exists()

    @pytest.mark.parametrize('is_finalized', [True, False])
    def test_delete_artifact__deletes_identifier_if_unreferenced(self, outcome, external_doi, is_finalized):
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()
        test_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.DATA, finalized=is_finalized
        )

        test_artifact.delete()
        assert not Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    @pytest.mark.parametrize('is_finalized', [True, False])
    def test_delete_artifact__keeps_identifier_if_osf_referent_exists(self, outcome, project_doi, is_finalized):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=is_finalized
        )

        test_artifact.delete()
        assert Identifier.objects.filter(value=TEST_PROJECT_DOI).exists()

    @pytest.mark.parametrize('is_finalized', [True, False])
    def test_delete_artifact__keeps_identifier_if_part_of_other_outcomes(self, outcome, external_doi, is_finalized):
        test_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.DATA, finalized=is_finalized
        )

        alternate_outcome = Outcome.objects.create()
        alternate_outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.ANALYTIC_CODE
        )

        test_artifact.delete()
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    @mock.patch('osf.models.registrations.update_doi_metadata_on_change')
    def test_doi_update__updated_on_finalize(self, mock_update_doi, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=False
        )
        test_artifact.finalize()
        mock_update_doi.assert_called_with(target_guid=outcome.primary_osf_resource._id)

    @mock.patch('osf.models.registrations.update_doi_metadata_on_change')
    def test_doi_update__updated_on_pid_update_if_finalized(self, mock_update_doi, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        test_artifact.update(new_pid_value='something')
        mock_update_doi.assert_called_with(target_guid=outcome.primary_osf_resource._id)

    @mock.patch('osf.models.registrations.update_doi_metadata_on_change')
    def test_doi_update__not_updated_on_non_pid_update(self, mock_update_doi, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        test_artifact.update(new_description='new', new_artifact_type=ArtifactTypes.MATERIALS)
        mock_update_doi.assert_not_called()

    @mock.patch('osf.models.registrations.update_doi_metadata_on_change')
    def test_doi_update__not_updated_on_pid_update_if_not_finalized(self, mock_update_doi, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=False
        )
        test_artifact.update(new_pid_value='something')
        mock_update_doi.assert_not_called()

    @mock.patch('osf.models.registrations.update_doi_metadata_on_change')
    def test_doi_update__updated_on_delete_if_finalized(self, mock_update_doi, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=True
        )
        test_artifact.delete()
        mock_update_doi.assert_called_with(target_guid=outcome.primary_osf_resource._id)

    @mock.patch('osf.models.registrations.update_doi_metadata_on_change')
    def test_doi_update__not_updated_on_delete_if_not_finalized(self, mock_update_doi, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA, finalized=False
        )
        test_artifact.delete()
        mock_update_doi.assert_not_called()
