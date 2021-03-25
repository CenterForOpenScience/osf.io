import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    ProjectFactory,
    NodeRelationFactory
)

from website.settings import API_DOMAIN


@pytest.mark.django_db
class TestSparseRegistration:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def linked_registration(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def linked_registration_private(self, user):
        return RegistrationFactory()

    @pytest.fixture()
    def registration(self, user, node, linked_registration, linked_registration_private):
        reg = RegistrationFactory(creator=user)

        NodeRelationFactory(
            child=node,
            parent=reg,
            is_node_link=True
        ).save()

        NodeRelationFactory(
            child=linked_registration,
            parent=reg,
            is_node_link=True
        ).save()

        NodeRelationFactory(
            child=linked_registration_private,
            parent=reg,
            is_node_link=True
        ).save()
        return reg

    @pytest.fixture()
    def sparse_linked_nodes_url(self, registration):
        return f'{API_DOMAIN}{API_BASE}sparse/registrations/{registration._id}/linked_nodes/'

    @pytest.fixture()
    def sparse_linked_registration_url(self, registration):
        return f'{API_DOMAIN}{API_BASE}sparse/registrations/{registration._id}/linked_registrations/'

    def test_linked_nodes(self, app, user, node, sparse_linked_nodes_url):
        res = app.get(sparse_linked_nodes_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == node._id

    def test_linked_registrations(self, app, user, linked_registration, sparse_linked_registration_url):
        res = app.get(sparse_linked_registration_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == linked_registration._id
