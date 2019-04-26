import pytest
from future.moves.urllib.parse import urlparse

from api_tests.nodes.views.test_node_contributors_list import NodeCRUDTestCase
from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    CommentFactory,
    RegistrationFactory,
    InstitutionFactory,
    WithdrawnRegistrationFactory,
)


class TestWithdrawnRegistrations(NodeCRUDTestCase):

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def registration(self, user, project_public, institution_one):
        registration = RegistrationFactory(creator=user, project=project_public)
        registration.affiliated_institutions.add(institution_one)
        return registration

    @pytest.fixture()
    def registration_with_child(self, user, project_public):
        project = ProjectFactory(creator=user, is_public=True)
        child = ProjectFactory(creator=user, is_public=True, parent=project)

        registration = RegistrationFactory(project=project, is_public=True)
        RegistrationFactory(project=child, is_public=True)
        return registration

    @pytest.fixture()
    def withdrawn_registration_with_child(self, user, registration_with_child):
        withdrawn_registration = WithdrawnRegistrationFactory(
            registration=registration_with_child, user=registration_with_child.creator)
        withdrawn_registration.justification = 'We made a major error.'
        withdrawn_registration.save()
        return withdrawn_registration

    @pytest.fixture()
    def withdrawn_registration(self, registration):
        withdrawn_registration = WithdrawnRegistrationFactory(
            registration=registration, user=registration.creator)
        withdrawn_registration.justification = 'We made a major error.'
        withdrawn_registration.save()
        return withdrawn_registration

    @pytest.fixture()
    def project_pointer_public(self):
        return ProjectFactory(is_public=True)

    @pytest.fixture()
    def pointer_public(self, user, project_public, project_pointer_public):
        return project_public.add_pointer(
            project_pointer_public, auth=Auth(user), save=True)

    @pytest.fixture()
    def url_withdrawn(self, registration):
        return '/{}registrations/{}/?version=2.2'.format(
            API_BASE, registration._id)

    def test_can_access_withdrawn_contributors(
            self, app, user, registration, withdrawn_registration):
        url = '/{}registrations/{}/contributors/'.format(
            API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_can_access_withdrawn_contributor_detail(
            self, app, user, registration):
        url = '/{}registrations/{}/contributors/{}/'.format(
            API_BASE, registration._id, user._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_cannot_errors(
            self, app, user, project_public, registration,
            withdrawn_registration, pointer_public):

        #   test_cannot_access_withdrawn_children
        url = '/{}registrations/{}/children/'.format(
            API_BASE, registration._id)
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
        url = '/{}registrations/{}/node_links/{}/'.format(
            API_BASE, registration._id, pointer_public._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_cannot_access_withdrawn_node_links_list
        url = '/{}registrations/{}/node_links/'.format(
            API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_cannot_access_withdrawn_registrations_list
        registration.save()
        url = '/{}registrations/{}/registrations/'.format(
            API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_cannot_access_withdrawn_comments(
            self, app, user, project_public, pointer_public,
            registration, withdrawn_registration):
        project_public = ProjectFactory(is_public=True, creator=user)
        CommentFactory(node=project_public, user=user)
        url = '/{}registrations/{}/comments/'.format(
            API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_cannot_access_withdrawn_node_logs(
            self, app, user, project_public, pointer_public,
            registration, withdrawn_registration):
        ProjectFactory(is_public=True, creator=user)
        url = '/{}registrations/{}/logs/'.format(API_BASE, registration._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_withdrawn_registrations_display_limited_attributes_fields(
            self, app, user, registration, withdrawn_registration, url_withdrawn):
        registration = registration
        res = app.get(url_withdrawn, auth=user.auth)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        registration.reload()
        expected_attributes = {
            'title': registration.title,
            'description': registration.description,
            'date_created': registration.created.isoformat().replace(
                '+00:00',
                'Z'),
            'date_registered': registration.registered_date.isoformat().replace(
                '+00:00',
                'Z'),
            'date_modified': registration.last_logged.isoformat().replace(
                '+00:00',
                'Z'),
            'date_withdrawn': registration.retraction.date_retracted.isoformat().replace(
                '+00:00',
                'Z'),
            'withdrawal_justification': registration.retraction.justification,
            'public': None,
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
            'registration_supplement': registration.registered_schema.first().name}

        for attribute in expected_attributes:
            assert expected_attributes[attribute] == attributes[attribute]

        contributors = urlparse(
            res.json['data']['relationships']['contributors']['links']['related']['href']).path
        assert contributors == '/{}registrations/{}/contributors/'.format(
            API_BASE, registration._id)

    def test_withdrawn_registrations_display_limited_relationship_fields(
            self, app, user, registration, withdrawn_registration):

        url_withdrawn = '/{}registrations/{}/?version=2.14'.format(API_BASE, registration._id)
        res = app.get(url_withdrawn, auth=user.auth)

        assert 'children' not in res.json['data']['relationships']
        assert 'comments' not in res.json['data']['relationships']
        assert 'node_links' not in res.json['data']['relationships']
        assert 'registrations' not in res.json['data']['relationships']
        assert 'parent' in res.json['data']['relationships']
        assert 'forked_from' not in res.json['data']['relationships']
        assert 'files' not in res.json['data']['relationships']
        assert 'logs' not in res.json['data']['relationships']
        assert 'registered_by' not in res.json['data']['relationships']
        assert 'registered_from' in res.json['data']['relationships']
        assert 'root' in res.json['data']['relationships']
        assert 'affiliated_institutions' in res.json['data']['relationships']
        assert 'license' not in res.json['data']['relationships']
        assert 'identifiers' in res.json['data']['relationships']

    def test_field_specific_related_counts_ignored_if_hidden_field_on_withdrawn_registration(
            self, app, user, registration, withdrawn_registration):
        url = '/{}registrations/{}/?related_counts=children'.format(
            API_BASE, registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert 'children' not in res.json['data']['relationships']
        assert 'contributors' in res.json['data']['relationships']

    def test_field_specific_related_counts_retrieved_if_visible_field_on_withdrawn_registration(
            self, app, user, registration, withdrawn_registration):
        url = '/{}registrations/{}/?related_counts=contributors'.format(
            API_BASE, registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['relationships']['contributors']['links']['related']['meta']['count'] == 1

    def test_child_inherits_withdrawl_justication_and_date_withdrawn(
            self, app, user, withdrawn_registration_with_child, registration_with_child):

        reg_child = registration_with_child.node_relations.first().child
        url = '/{}registrations/{}/?version=2.2'.format(API_BASE, reg_child._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['withdrawal_justification'] == withdrawn_registration_with_child.justification
        formatted_date_retracted = withdrawn_registration_with_child.date_retracted.isoformat().replace('+00:00', 'Z')
        assert res.json['data']['attributes']['date_withdrawn'] == formatted_date_retracted
