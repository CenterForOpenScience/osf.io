import pytest

from api.users.serializers import UserSerializer
from osf_tests.factories import (
    UserFactory,
    RegistrationFactory,
    WithdrawnRegistrationFactory,
    PreprintFactory,
    ProjectFactory,
)
from tests.utils import make_drf_request_with_version
from django.utils import timezone


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def user_without_nodes():
    return UserFactory()


@pytest.fixture()
def preprint(user):
    return PreprintFactory(creator=user)


@pytest.fixture()
def unpublished_preprint(user):
    return PreprintFactory(is_published=False, creator=user)


@pytest.fixture()
def deleted_preprint(user):
    preprint = PreprintFactory(creator=user)
    preprint.deleted = timezone.now()
    preprint.save()
    return preprint


@pytest.fixture()
def withdrawn_preprint(user):
    preprint = PreprintFactory(is_published=False, creator=user)
    preprint.date_withdrawn = timezone.now()
    preprint.save()
    return preprint


@pytest.fixture()
def private_preprint(user):
    preprint = PreprintFactory(creator=user)
    preprint.is_public = False
    preprint.save()
    return preprint


@pytest.fixture()
def registration(user):
    return RegistrationFactory(creator=user, is_public=True)


@pytest.fixture()
def withdrawn_registration(registration):
    return WithdrawnRegistrationFactory(registration=registration, user=registration.creator)


@pytest.fixture()
def private_registration(user):
    return RegistrationFactory(creator=user, is_public=False)


@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)


@pytest.fixture()
def public_project(user):
    return ProjectFactory(creator=user, is_public=True)


@pytest.fixture()
def deleted_project(user):
    return ProjectFactory(creator=user, is_deleted=True)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestUserSerializer:

    def get_data(self, user, with_auth=None):
        req = make_drf_request_with_version(version='2.0')
        req.query_params['related_counts'] = True
        if with_auth:
            req.user = with_auth
        result = UserSerializer(user, context={'request': req}).data
        return result['data']

    def test_user_serializer(self, user):

        data = self.get_data(user)
        assert data['id'] == user._id
        assert data['type'] == 'users'

        # Attributes
        attributes = data['attributes']
        assert attributes['family_name'] == user.family_name
        assert attributes['given_name'] == user.given_name
        assert attributes['active'] == user.is_active
        assert attributes['employment'] == user.jobs
        assert attributes['education'] == user.schools

        # Relationships
        relationships = data['relationships']
        assert 'quickfiles' in relationships
        assert 'nodes' in relationships
        assert 'institutions' in relationships
        assert 'preprints' in relationships
        assert 'registrations' in relationships

    def test_user_serializer_with_related_counts(self, user):
        data = self.get_data(user)

        # Relationships
        relationships = data['relationships']
        assert relationships['quickfiles']['links']['related']['meta']['count'] == 0
        assert relationships['nodes']['links']['related']['meta']['count'] == 0
        assert relationships['institutions']['links']['related']['meta']['count'] == 0
        assert relationships['preprints']['links']['related']['meta']['count'] == 0
        assert relationships['registrations']['links']['related']['meta']['count'] == 0

    def test_user_serializer_get_nodes_count(self,
                                             user,
                                             user_without_nodes,
                                             project,
                                             public_project,
                                             deleted_project):

        data = self.get_data(user, with_auth=user)
        assert user.nodes.exclude(type='osf.quickfilesnode').count() == 3
        assert data['relationships']['nodes']['links']['related']['meta']['count'] == 2

        data = self.get_data(user, with_auth=user_without_nodes)
        assert user_without_nodes.nodes.exclude(type='osf.quickfilesnode').count() == 0
        assert data['relationships']['nodes']['links']['related']['meta']['count'] == 1

        data = self.get_data(user, with_auth=None)
        assert data['relationships']['nodes']['links']['related']['meta']['count'] == 1

    def test_user_serializer_get_registration_count(self,
                                                    user,
                                                    user_without_nodes,
                                                    registration,
                                                    private_registration,
                                                    withdrawn_registration):

        data = self.get_data(user, with_auth=user)
        assert user.nodes.filter(type='osf.registration').count() == 2
        assert data['relationships']['registrations']['links']['related']['meta']['count'] == 2

        data = self.get_data(user, with_auth=user_without_nodes)
        assert user_without_nodes.nodes.filter(type='osf.registration').count() == 0
        assert data['relationships']['registrations']['links']['related']['meta']['count'] == 1

        data = self.get_data(user, with_auth=None)
        assert data['relationships']['registrations']['links']['related']['meta']['count'] == 1

    def test_user_serializer_get_preprint_count(self,
                                                user,
                                                user_without_nodes,
                                                preprint,
                                                private_preprint,
                                                withdrawn_preprint,
                                                unpublished_preprint,
                                                deleted_preprint):

        data = self.get_data(user, with_auth=user)
        assert user.preprints.count() == 5
        assert data['relationships']['preprints']['links']['related']['meta']['count'] == 2

        data = self.get_data(user, with_auth=user_without_nodes)
        assert user_without_nodes.preprints.count() == 0
        assert data['relationships']['preprints']['links']['related']['meta']['count'] == 1

        data = self.get_data(user, with_auth=None)
        assert user_without_nodes.preprints.count() == 0
        assert data['relationships']['preprints']['links']['related']['meta']['count'] == 1
