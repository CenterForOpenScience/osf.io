import pytest
from osf.models import Identifier, Outcome, OutcomeArtifact
from osf.utils.outcomes import ArtifactTypes, NoPIDError
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

    @pytest.mark.parametrize('doi_value', [TEST_PROJECT_DOI, TEST_EXTERNAL_DOI])
    def test_create_artifact_from_known_identifier(
        self, outcome, project_doi, external_doi, doi_value
    ):
        new_artifact = OutcomeArtifact.objects.create_for_identifier_value(
            outcome=outcome,
            pid_value=TEST_PROJECT_DOI,
            artifact_type=ArtifactTypes.MATERIALS
        )

        assert new_artifact.identifier == project_doi
        assert new_artifact.outcome == outcome
        assert new_artifact.artifact_type == ArtifactTypes.MATERIALS

    def test_create_artifact_from_unknown_identifier__create(self, outcome):
        assert not Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

        new_artifact = OutcomeArtifact.objects.create_for_identifier_value(
            outcome=outcome,
            pid_value=TEST_EXTERNAL_DOI,
            create_identifier=True,
            artifact_type=ArtifactTypes.CODE,
        )

        created_identifier = Identifier.objects.get(value=TEST_EXTERNAL_DOI)
        assert new_artifact.identifier == created_identifier

    def test_create_artifact_from_unknown_identifer__no_create(self, outcome):
        with pytest.raises(NoPIDError):
            OutcomeArtifact.objects.create_for_identifier_value(
                outcome=outcome,
                pid_value=TEST_EXTERNAL_DOI,
                create_identifier=False,
                artifact_type=ArtifactTypes.SUPPLEMENTS
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
            identifier=external_doi, artifact_type=ArtifactTypes.CODE
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

    def test_update_identifier__get_existing_identifier(self, outcome, project_doi, external_doi):
        test_artifact = outcome.artifact_metadata.create(artifact_type=ArtifactTypes.DATA)
        test_artifact.update_identifier(new_pid_value=TEST_PROJECT_DOI)
        assert test_artifact.identifier == project_doi

    def test_update_identifier__create_new_identifier(self, outcome, project_doi):
        assert not Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

        test_artifact = outcome.artifact_metadata.create(artifact_type=ArtifactTypes.DATA)
        test_artifact.update_identifier(new_pid_value=TEST_EXTERNAL_DOI)

        assert test_artifact.identifier.value == TEST_EXTERNAL_DOI
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    def test_update_identifier__deletes_previous_identifier_if_unreferenced(self, outcome, project_doi, external_doi):
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()
        test_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.DATA
        )
        assert test_artifact.identifier != project_doi

        test_artifact.update_identifier(new_pid_value=project_doi.value)
        assert test_artifact.identifier == project_doi
        assert not Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    def test_update_identifier__keeps_previous_identifier_if_osf_referent_exists(self, outcome, project_doi):
        assert Identifier.objects.filter(value=TEST_PROJECT_DOI).exists()
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        test_artifact.update_identifier(new_pid_value=TEST_EXTERNAL_DOI)
        assert test_artifact.identifier != project_doi
        assert Identifier.objects.filter(value=TEST_PROJECT_DOI).exists()

    def test_update_identifier__keeps_previous_identifier_if_part_of_other_outcomes(
        self, outcome, project_doi, external_doi
    ):
        test_artifact = outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.DATA
        )
        alternate_outcome = Outcome.objects.create()
        alternate_outcome.artifact_metadata.create(
            identifier=external_doi, artifact_type=ArtifactTypes.CODE
        )

        test_artifact.update_identifier(new_pid_value=project_doi.value)
        assert test_artifact.identifier == project_doi
        assert Identifier.objects.filter(value=TEST_EXTERNAL_DOI).exists()

    def test_update_identifier__no_change_if_same_pid(self, outcome, project_doi):
        test_artifact = outcome.artifact_metadata.create(
            identifier=project_doi, artifact_type=ArtifactTypes.DATA
        )

        test_artifact.update_identifier(new_pid_value=project_doi.value)
        assert test_artifact.identifier == project_doi
