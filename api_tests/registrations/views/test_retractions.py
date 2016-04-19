from urlparse import urlparse
from api_tests.nodes.views.test_node_contributors_list import NodeCRUDTestCase

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth

from tests.base import fake
from tests.factories import (
    ProjectFactory,
    CommentFactory,
    RegistrationFactory,
    RetractedRegistrationFactory,

)

class TestRetractions(NodeCRUDTestCase):

    def setUp(self):
        super(TestRetractions, self).setUp()
        self.registration = RegistrationFactory(creator=self.user, project=self.public_project)
        self.retraction = RetractedRegistrationFactory(registration=self.registration, user=self.registration.creator)

        self.public_pointer_project = ProjectFactory(is_public=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.retraction_url = '/{}registrations/{}/'.format(API_BASE, self.registration._id)
        self.retraction.justification = 'We made a major error.'
        self.retraction.save()

    def test_can_access_retracted_contributors(self):
        url = '/{}registrations/{}/contributors/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_cannot_access_retracted_children(self):
        url = '/{}registrations/{}/children/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannot_access_retracted_comments(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        url = '/{}registrations/{}/comments/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_can_access_retracted_contributor_detail(self):
        url = '/{}registrations/{}/contributors/{}/'.format(API_BASE, self.registration._id, self.user._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_cannot_return_a_retraction_at_node_detail_endpoint(self):
        url = '/{}nodes/{}/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_cannot_update_a_retraction(self):
        url = '/{}registrations/{}/'.format(API_BASE, self.registration._id)
        res = self.app.put_json_api(url, {
            'data': {
                'id': self.registration._id,
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'hypothesis',
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        self.registration.reload()
        assert_equal(res.status_code, 405)
        assert_equal(self.registration.title, self.registration.title)
        assert_equal(self.registration.description, self.registration.description)

    def test_cannot_delete_a_retraction(self):
        url = '/{}registrations/{}/'.format(API_BASE, self.registration._id)
        res = self.app.delete_json_api(url, auth=self.user.auth, expect_errors=True)
        self.registration.reload()
        assert_equal(res.status_code, 405)
        assert_equal(self.registration.title, self.registration.title)
        assert_equal(self.registration.description, self.registration.description)

    def test_cannot_access_retracted_files_list(self):
        url = '/{}registrations/{}/files/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannot_access_retracted_node_links_detail(self):
        url = '/{}registrations/{}/node_links/{}/'.format(API_BASE, self.registration._id, self.public_pointer._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannot_access_retracted_node_links_list(self):
        url = '/{}registrations/{}/node_links/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannot_access_retracted_node_logs(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        url = '/{}registrations/{}/logs/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannot_access_retracted_registrations_list(self):
        self.registration.save()
        url = '/{}registrations/{}/registrations/'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_retractions_display_limited_fields(self):
        registration = self.registration
        res = self.app.get(self.retraction_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        expected_attributes = {
            'title': registration.title,
            'description': registration.description,
            'date_created': registration.date_created.isoformat(),
            'date_registered': registration.registered_date.isoformat(),
            'withdrawal_justification': registration.retraction.justification,
            'public': None,
            'category': None,
            'date_modified': None,
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
            'registration_supplement': registration.registered_schema[0].name
        }

        for attribute in expected_attributes:
            assert_equal(expected_attributes[attribute], attributes[attribute])

        contributors = urlparse(res.json['data']['relationships']['contributors']['links']['related']['href']).path
        assert_equal(contributors, '/{}registrations/{}/contributors/'.format(API_BASE, registration._id))

        assert_not_in('children', res.json['data']['relationships'])
        assert_not_in('comments', res.json['data']['relationships'])
        assert_not_in('node_links', res.json['data']['relationships'])
        assert_not_in('registrations', res.json['data']['relationships'])
        assert_not_in('parent', res.json['data']['relationships'])
        assert_not_in('forked_from', res.json['data']['relationships'])
        assert_not_in('files', res.json['data']['relationships'])
        assert_not_in('logs', res.json['data']['relationships'])
        assert_not_in('primary_institution', res.json['data']['relationships'])
        assert_not_in('registered_by', res.json['data']['relationships'])
        assert_not_in('registered_from', res.json['data']['relationships'])
        assert_not_in('root', res.json['data']['relationships'])

    def test_field_specific_related_counts_ignored_if_hidden_field_on_retraction(self):
        url = '/{}registrations/{}/?related_counts=children'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_not_in('children', res.json['data']['relationships'])
        assert_in('contributors', res.json['data']['relationships'])

    def test_field_specific_related_counts_retrieved_if_visible_field_on_retraction(self):
        url = '/{}registrations/{}/?related_counts=contributors'.format(API_BASE, self.registration._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['relationships']['contributors']['links']['related']['meta']['count'], 1)

