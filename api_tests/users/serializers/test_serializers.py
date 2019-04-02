import pytest

from api.users.serializers import UserSerializer
from api_tests.utils import create_test_file

from osf_tests.factories import (
    UserFactory,
    RegistrationFactory,
    WithdrawnRegistrationFactory,
    PreprintFactory,
    ProjectFactory,
    InstitutionFactory,
    OSFGroupFactory,
)
from tests.utils import make_drf_request_with_version
from django.utils import timezone
from django.urls import resolve, reverse

from osf.models import QuickFilesNode

@pytest.fixture()
def user():
    user = UserFactory()
    quickfiles_node = QuickFilesNode.objects.get_for_user(user)
    create_test_file(quickfiles_node, user)
    inst = InstitutionFactory()
    user.affiliated_institutions.add(inst)
    return user


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

@pytest.fixture()
def group(user):
    return OSFGroupFactory(creator=user, name='Platform')

@pytest.fixture()
def group_project(group):
    project = ProjectFactory()
    project.add_osf_group(group)
    return project


def pytest_generate_tests(metafunc):
    # called once per each test function
    funcarglist = metafunc.cls.params.get(metafunc.function.__name__)
    if not funcarglist:
        return
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(argnames, [[funcargs[name] for name in argnames]
            for funcargs in funcarglist])

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestUserSerializer:

    params = {
        'test_related_counts_equal_related_views': [{
            'field_name': 'nodes',
            'expected_count': {
                'user': 5,  # this counts the private nodes created by RegistrationFactory
                'other_user': 1,
                'no_auth': 1
            },
        }, {
            'field_name': 'preprints',  # "unpublished" preprints don't appear in api at all
            'expected_count': {
                'user': 2,
                'other_user': 1,
                'no_auth': 1
            },
        }, {
            'field_name': 'registrations',
            'expected_count': {
                'user': 2,
                'other_user': 1,
                'no_auth': 1
            },
        }, {
            'field_name': 'institutions',
            'expected_count': {
                'user': 1,
                'other_user': 1,
                'no_auth': 1
            },
        }, {
            'field_name': 'quickfiles',
            'expected_count': {
                'user': 1,
                'other_user': 1,
                'no_auth': 1
            },
        }]
    }

    def get_data(self, user):
        req = make_drf_request_with_version(version='2.0')
        req.query_params['related_counts'] = True
        req.user = user
        result = UserSerializer(user, context={'request': req}).data
        return result['data']

    def get_related_count(self, user, related_field, auth):
        req = make_drf_request_with_version(version='2.0')
        req.query_params['related_counts'] = True
        if auth:
            req.user = auth
        result = UserSerializer(user, context={'request': req}).data
        return result['data']['relationships'][related_field]['links']['related']['meta']['count']

    def get_view_count(self, user, related_field, auth):
        req = make_drf_request_with_version(version='2.0')
        if auth:
            req.user = auth
        view_name = UserSerializer().fields[related_field].field.view_name
        resolve_match = resolve(reverse(view_name, kwargs={'version': 'v2', 'user_id': user._id}))
        view = resolve_match.func.view_class(request=req, kwargs={'version': 'v2', 'user_id': user._id})

        return view.get_queryset().count()

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
        assert 'groups' in relationships

    def test_related_counts_equal_related_views(self,
                                                request,
                                                field_name,
                                                expected_count,
                                                user,
                                                user_without_nodes,
                                                project,
                                                public_project,
                                                deleted_project,
                                                registration,
                                                private_registration,
                                                withdrawn_registration,
                                                preprint,
                                                private_preprint,
                                                withdrawn_preprint,
                                                unpublished_preprint,  # not in the view/related counts by default
                                                deleted_preprint,
                                                group,
                                                group_project):

        view_count = self.get_view_count(user, field_name, auth=user)
        related_count = self.get_related_count(user, field_name, auth=user)

        assert related_count == view_count == expected_count['user']

        view_count = self.get_view_count(user, field_name, auth=user_without_nodes)
        related_count = self.get_related_count(user, field_name, auth=user_without_nodes)

        assert related_count == view_count == expected_count['other_user']

        view_count = self.get_view_count(user, field_name, auth=None)
        related_count = self.get_related_count(user, field_name, auth=None)

        assert related_count == view_count == expected_count['no_auth']
