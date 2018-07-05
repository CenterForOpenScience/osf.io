import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def registration_with_children(user):
    project = ProjectFactory(creator=user)
    NodeFactory(parent=project, creator=user)
    NodeFactory(parent=project, creator=user)
    return RegistrationFactory(
        project=project
    )

@pytest.fixture()
def registration_with_children_url(registration_with_children):
    return '/{}registrations/{}/children/'.format(
        API_BASE,
        registration_with_children._id,
    )


@pytest.fixture()
def registration_with_children_approved(user, registration_with_children):

    registration_with_children._initiate_approval(user)
    approval_token = registration_with_children.registration_approval.approval_state[user._id]['approval_token']
    registration_with_children.registration_approval.approve(user, approval_token)

    return registration_with_children

@pytest.fixture()
def registration_with_children_approved_url(registration_with_children_approved):
    return '/{}registrations/{}/children/'.format(
        API_BASE,
        registration_with_children_approved._id,
    )

@pytest.mark.django_db
class TestRegistrationsChildrenList:

    def test_registrations_children_list(self, user, app, registration_with_children, registration_with_children_url):
        component_one, component_two = registration_with_children.nodes

        res = app.get(registration_with_children_url, auth=user.auth)
        ids = [node['id'] for node in res.json['data']]

        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert component_one._id in ids
        assert component_two._id in ids

    def test_return_registrations_list_no_auth_approved(self, user, app, registration_with_children_approved, registration_with_children_approved_url):
        component_one, component_two = registration_with_children_approved.nodes

        res = app.get(registration_with_children_approved_url)
        ids = [node['id'] for node in res.json['data']]

        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert component_one._id in ids
        assert component_two._id in ids

    def test_registrations_list_no_auth_unapproved(self, user, app, registration_with_children, registration_with_children_url):
        res = app.get(registration_with_children_url, expect_errors=True)

        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'


@pytest.mark.django_db
class TestRegistrationChildrenListFiltering:

    def test_registration_child_filtering(self, app, user, registration_with_children):
        component_one, component_two = registration_with_children.nodes

        url = '/{}registrations/{}/children/?filter[title]={}'.format(
            API_BASE,
            registration_with_children._id,
            component_one.title
        )
        res = app.get(url, auth=user.auth)
        ids = [node['id'] for node in res.json['data']]

        assert component_one._id in ids
        assert component_two._id not in ids
