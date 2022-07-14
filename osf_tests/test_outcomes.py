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


@pytest.mark.django_db
class TestOutcomeForRegistration:

    def test_get_outcome___exists(self, registration, registration_doi):
        new_outcome = Outcome.objects.create()
        OutcomeArtifact.objects.create(
            outcome=new_outcome,
            identifier=registration_doi,
            artifact_type=ArtifactTypes.PRIMARY
        )

        stored_outcome = Outcome.objects.for_registration(registration, creaate=False)
        assert stored_outcome.id == new_outcome.id

    def test_get_outcome__none_exists(self, registration, registration_doi):
        assert not Outcome.objects.for_registration(registration, create=False)

    def test_get_outcome__no_identifier(self, registration):
        with pytest.raises(NoPIDError):
            Outcome.objects.for_registration(registration)

    def test_create_outcome__creates(self, registration, registration_doi):
        assert not Outcome.objects.exists()
        Outcome.objects.for_registration(registration, create=True)
        assert Outcome.objects.exists()

    def test_create_outcome__no_identifier(self, registration):
        with pytest.raises(NoPIDError):
            Outcome.objects.for_registration(registration, create=True)

    def test_create_outcome__creates_primary_artifact(self, registration, registration_doi):
        outcome = Outcome.objects.for_registration(registration, create=True)

        assert outcome.artifacts.count() == 1
        primary_artifact = outcome.artifacts.through.objects.get()
        assert primary_artifact.identifier == registration_doi
        assert primary_artifact.pid == registration_doi.value
        assert primary_artifact.artifact_type == ArtifactTypes.PRIMARY

    def test_create_outcome__copies_metadata(self, registration, registration_doi):
        outcome = Outcome.objects.for_registration(registration, create=True)
        assert outcome.title == registration.title
        assert outcome.description == registration.description
        assert outcome.category == registration.category


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
        outcome.add_artifact(project_doi, ArtifactTypes.MATERIALS)
        outcome.add_artifact(external_doi, ArtifactTypes.SUPPLEMENTS)

        bogus_outcome = Outcome.objects.create()
        bogus_outcome.add_artifact(external_doi, ArtifactTypes.CODE)

        registration_artifacts = OutcomeArtifact.objects.for_registration(registration)
        assert registration_artifacts.count() == 2

        project_artifact = registration_artifacts.get(identifier=project_doi)
        assert project_artifact.outcome == outcome
        assert project_artifact.artifact_type == ArtifactTypes.MATERIALS
        assert project_artifact.pid == project_doi.value

        external_artifact = registration_artifacts.get(identifier=external_doi)
        assert external_artifact.outcome == outcome
        assert external_artifact.artifact_type == ArtifactTypes.SUPPLEMENTS
        assert external_artifact.pid == external_doi.value
