import pytest
from framework.auth.core import Auth

from osf_tests.factories import ProjectFactory, AuthUserFactory, RegistrationFactory, WithdrawnRegistrationFactory
from api.base.settings.defaults import API_BASE


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class TestNodeLinkedByNodesList:
    @pytest.fixture()
    def project_public(self, user):
        return ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def project_private(self, user):
        return ProjectFactory(
            title='Project Two',
            is_public=False,
            creator=user)

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/linked_by_nodes/'.format(API_BASE, project_public._id)

    def test_linked_by_nodes_lists_nodes(self, app, url_public, user, project_public, project_private):
        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 0

        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == project_private._id

    def test_linked_by_nodes_doesnt_list_registrations(self, app, url_public, user, project_public, project_private):
        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == project_private._id

        # registration will have the same links as its model project
        registration = RegistrationFactory(project=project_private, creator=user)
        project_public.reload()

        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] != registration._id

    def test_linked_by_nodes_respect_permissions(self, app, url_public, user, project_public, project_private):
        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == project_private._id

        res = app.get(url_public)
        assert len(res.json['data']) == 0

    def test_linked_by_nodes_doesnt_show_deleted(self, app, url_public, user, project_public, project_private):
        project_private.add_pointer(project_public, auth=Auth(user), save=True)

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == project_private._id

        project_private.is_deleted = True
        project_private.save()
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 0


@pytest.mark.django_db
class TestNodeLinkedByRegistrationsList:
    @pytest.fixture()
    def project_public(self, user):
        return ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def project_private(self, user):
        return ProjectFactory(
            title='Project Two',
            is_public=False,
            creator=user)

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/linked_by_registrations/'.format(API_BASE, project_public._id)

    def test_linked_by_registrations_links_registrations(self, app, url_public, user, project_public, project_private):
        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 0

        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        # registration will have the same links as its model project
        registration = RegistrationFactory(project=project_private, creator=user)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == registration._id

    def test_linked_by_registrations_doesnt_list_nodes(self, app, url_public, user, project_public, project_private):
        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 0

    def test_linked_by_registrations_respect_permissions(self, app, url_public, user, project_public, project_private):
        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        registration = RegistrationFactory(project=project_private, creator=user)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == registration._id

        res = app.get(url_public)
        assert len(res.json['data']) == 0

    def test_linked_by_registrations_doesnt_show_retracted(self, app, url_public, user, project_public, project_private):
        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        registration = RegistrationFactory(project=project_private, creator=user)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == registration._id

        WithdrawnRegistrationFactory(registration=registration, user=user)
        project_public.reload()

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 0
