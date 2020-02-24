import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    PrivateLinkFactory,
)


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def registration_with_children(user):
    project = ProjectFactory(creator=user)
    NodeFactory(parent=project, creator=user)
    NodeFactory(parent=project, creator=user)
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
def view_only_link(registration_with_children):
    view_only_link = PrivateLinkFactory(name='testlink')
    view_only_link.nodes.add(registration_with_children)
    view_only_link.save()
    return view_only_link

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
        component_one, component_two, component_three, component_four = registration_with_children.nodes

        res = app.get(registration_with_children_url, auth=user.auth)
        ids = [node['id'] for node in res.json['data']]

        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert component_one._id in ids
        assert component_two._id in ids

    def test_return_registrations_list_no_auth_approved(self, user, app, registration_with_children_approved, registration_with_children_approved_url):
        component_one, component_two, component_three, component_four = registration_with_children_approved.nodes

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

    def test_registration_children_no_auth_vol(self, user, app, registration_with_children,
            registration_with_children_url, view_only_link):
        # viewed through private link
        component_one, component_two, component_three, component_four = registration_with_children.nodes

        # get registration related_counts with vol before vol is attached to components
        node_url = '/{}registrations/{}/?related_counts=children&view_only={}'.format(API_BASE,
            registration_with_children._id, view_only_link.key)
        res = app.get(node_url)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0

        # view only link is not attached to components
        view_only_link_url = '{}?view_only={}'.format(registration_with_children_url, view_only_link.key)
        res = app.get(view_only_link_url)
        ids = [node['id'] for node in res.json['data']]
        assert res.status_code == 200
        assert len(ids) == 0
        assert component_one._id not in ids
        assert component_two._id not in ids

        # view only link now attached to components
        view_only_link.nodes.add(component_one)
        view_only_link.nodes.add(component_two)
        view_only_link.nodes.add(component_three)
        view_only_link.nodes.add(component_four)
        res = app.get(view_only_link_url)
        ids = [node['id'] for node in res.json['data']]
        assert res.status_code == 200
        assert component_one._id in ids
        assert component_two._id in ids

        # get registration related_counts with vol once vol is attached to components
        res = app.get(node_url)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 4

        # make private vol anonymous
        view_only_link.anonymous = True
        view_only_link.save()
        res = app.get(view_only_link_url)
        assert 'contributors' not in res.json['data'][0]['relationships']

        child_ids = [item['id'] for item in res.json['data']]
        assert component_one._id in child_ids
        assert component_two._id in child_ids
        assert component_three._id in child_ids
        assert component_four._id in child_ids

        # delete vol
        view_only_link.is_deleted = True
        view_only_link.save()
        res = app.get(view_only_link_url, expect_errors=True)
        assert res.status_code == 401


@pytest.mark.django_db
class TestRegistrationChildrenListFiltering:

    def test_registration_child_filtering(self, app, user, registration_with_children):
        component_one, component_two, component_three, component_four = registration_with_children.nodes

        url = '/{}registrations/{}/children/?filter[title]={}'.format(
            API_BASE,
            registration_with_children._id,
            component_one.title
        )
        res = app.get(url, auth=user.auth)
        ids = [node['id'] for node in res.json['data']]

        assert component_one._id in ids
        assert component_two._id not in ids
