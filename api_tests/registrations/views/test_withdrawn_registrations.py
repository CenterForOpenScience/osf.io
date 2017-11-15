import pytest
from urlparse import urlparse

from api_tests.nodes.views.test_node_contributors_list import NodeCRUDTestCase
from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from tests.base import fake
from osf_tests.factories import (
    ProjectFactory,
    CommentFactory,
    RegistrationFactory,
    WithdrawnRegistrationFactory,
)


class TestWithdrawnRegistrations(NodeCRUDTestCase):

    @pytest.fixture()
    def registration(self, user, project_public):
        return RegistrationFactory(creator=user, project=project_public)

    @pytest.fixture()
    def withdrawn_registration(self, registration):
        withdrawn_registration = WithdrawnRegistrationFactory(registration=registration, user=registration.creator)
        withdrawn_registration.justification = 'We made a major error.'
        withdrawn_registration.save()
        return withdrawn_registration

    @pytest.fixture()
    def project_pointer_public(self):
        return ProjectFactory(is_public=True)


    @pytest.fixture()
    def pointer_public(self, user, project_public, project_pointer_public):
        return project_public.add_pointer(project_pointer_public, auth=Auth(user), save=True)

    @pytest.fixture()
    def url_withdrawn(self, registration):
        return '/{}registrations/{}/?version=2.2'.format(API_BASE, registration._id)

    def test_can_access_withdrawn_contributors(self, app, user, registration, withdrawn_registration):
        url = '/{}registrations/{}/contributors/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_can_access_withdrawn_contributor_detail(self, app, user, registration):
        url = '/{}registrations/{}/contributors/{}/'.format(API_BASE, registration._id, user._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_cannot_errors(self, app, user, project_public, registration, withdrawn_registration, pointer_public):

    #   test_cannot_access_withdrawn_children
        url = '/{}registrations/{}/children/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_cannot_return_a_withdrawn_registration_at_node_detail_endpoint
        url = '/{}nodes/{}/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_cannot_delete_a_withdrawn_registration
        url = '/{}registrations/{}/'.format(API_BASE, registration._id)
        res = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        registration.reload()
        assert res.status_code == 405

    #   test_cannot_access_withdrawn_files_list
        url = '/{}registrations/{}/files/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_cannot_access_withdrawn_node_links_detail
        url = '/{}registrations/{}/node_links/{}/'.format(API_BASE, registration._id, pointer_public._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_cannot_access_withdrawn_node_links_list
        url = '/{}registrations/{}/node_links/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_cannot_access_withdrawn_registrations_list
        registration.save()
        url = '/{}registrations/{}/registrations/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_cannot_access_withdrawn_comments(self, app, user, project_public, pointer_public, registration, withdrawn_registration):
        project_public = ProjectFactory(is_public=True, creator=user)
        comment_public = CommentFactory(node=project_public, user=user)
        url = '/{}registrations/{}/comments/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_cannot_access_withdrawn_node_logs(self, app, user, project_public, pointer_public, registration, withdrawn_registration):
        project_public = ProjectFactory(is_public=True, creator=user)
        url = '/{}registrations/{}/logs/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_withdrawn_registrations_display_limited_fields(self, app, user, registration, withdrawn_registration, url_withdrawn):
        registration = registration
        res = app.get(url_withdrawn, auth=user.auth)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        registration.reload()
        expected_attributes = {
            'title': registration.title,
            'description': registration.description,
            'date_created': registration.date_created.isoformat().replace('+00:00', 'Z'),
            'date_registered': registration.registered_date.isoformat().replace('+00:00', 'Z'),
            'date_modified': registration.date_modified.isoformat().replace('+00:00', 'Z'),
            'date_withdrawn': registration.retraction.date_retracted.isoformat().replace('+00:00', 'Z'),
            'withdrawal_justification': registration.retraction.justification,
            'public': None,
            'category': None,
            'registration': True,
            'fork': None,
            'collection': None,
            'tags': None,
            'withdrawn': True,
            'pending_withdrawal': None,
            'pending_registration_approval': None,
            'pending_embargo_approval': None,
            'embargo_end_date': None,
            'registered_meta': None,
            'current_user_permissions': None,
            'registration_supplement': registration.registered_schema.first().name
        }

        for attribute in expected_attributes:
            assert expected_attributes[attribute] == attributes[attribute]

        contributors = urlparse(res.json['data']['relationships']['contributors']['links']['related']['href']).path
        assert contributors == '/{}registrations/{}/contributors/'.format(API_BASE, registration._id)

        assert 'children' not in res.json['data']['relationships']
        assert 'comments' not in res.json['data']['relationships']
        assert 'node_links' not in res.json['data']['relationships']
        assert 'registrations' not in res.json['data']['relationships']
        assert 'parent' not in res.json['data']['relationships']
        assert 'forked_from' not in res.json['data']['relationships']
        assert 'files' not in res.json['data']['relationships']
        assert 'logs' not in res.json['data']['relationships']
        assert 'registered_by' not in res.json['data']['relationships']
        assert 'registered_from' not in res.json['data']['relationships']
        assert 'root' not in res.json['data']['relationships']

    def test_field_specific_related_counts_ignored_if_hidden_field_on_withdrawn_registration(self, app, user, registration, withdrawn_registration):
        url = '/{}registrations/{}/?related_counts=children'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert 'children' not in res.json['data']['relationships']
        assert 'contributors' in res.json['data']['relationships']

    def test_field_specific_related_counts_retrieved_if_visible_field_on_withdrawn_registration(self, app, user, registration, withdrawn_registration):
        url = '/{}registrations/{}/?related_counts=contributors'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['relationships']['contributors']['links']['related']['meta']['count'] == 1

