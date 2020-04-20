# encoding: utf-8
import pytest

from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
)

from osf.management.commands.sync_registration_creator_bibliographic_status import (
    sync_registration_creator_bibliographic_status
)

from osf.models import Registration


@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def project(user):
    project = ProjectFactory(creator=user)
    return project

@pytest.fixture()
def project_contributor(user, project):
    contributor = project.contributor_set.get(user=user)
    contributor.visible = False
    contributor.save()
    return contributor

@pytest.fixture()
def registration(project, user):
    registration = RegistrationFactory(project=project, creator=user)
    return registration

@pytest.fixture()
def registration_creator_contrib(user, registration):
    contributor = registration.contributor_set.get(user=user)
    contributor.visible = True
    contributor.save()
    return contributor


@pytest.mark.django_db
class TestRegistrationCreatorBibliographicStatusSync:

    def test_sync_different_registration_creator_bibliographic_status(self, user, project, registration, project_contributor, registration_creator_contrib):
        # Assert out-of-sync bibliographic status
        assert project_contributor.visible is False
        assert registration_creator_contrib.visible is True

        registration_guid = registration._id
        sync_registration_creator_bibliographic_status(registration_guid)
        updated_registration = Registration.load(registration_guid)
        updated_registration_creator_contrib = updated_registration.contributor_set.get(user=registration.creator)
        assert updated_registration_creator_contrib.visible is False
        assert updated_registration_creator_contrib.visible == project_contributor.visible

    def test_sync_same_registration_creator_bibliographic_status(self, user, project, registration, registration_creator_contrib):
        # Assert aligned bibliographic status
        project_contributor = registration.registered_from.contributor_set.get(user=user)
        assert project_contributor.visible is True
        assert registration_creator_contrib.visible is True

        registration_guid = registration._id
        sync_registration_creator_bibliographic_status(registration_guid)
        updated_registration = Registration.load(registration_guid)
        updated_registration_creator_contrib = updated_registration.contributor_set.get(user=registration.creator)
        assert updated_registration_creator_contrib.visible is True
        assert updated_registration_creator_contrib.visible == project_contributor.visible
