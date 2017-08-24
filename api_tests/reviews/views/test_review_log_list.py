import mock
import pytest

from api.base.settings.defaults import API_BASE

from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory,
)

from tests.base import ApiTestCase

from website.util import permissions as osf_permissions

from reviews.permissions import GroupHelper
from reviews.models import ReviewLog


# include log list mixin
# test logs from multiple providers

class TestReviewLogCreate(ApiTestCase):
    def create_payload(self, reviewable_id=None, **attrs):
        payload = {
            'data': {
                'attributes': attrs,
                'relationships': {},
                'type': 'review_logs'
            }
        }
        if reviewable_id:
            payload['data']['relationships']['reviewable'] = {
                'data': {
                    'type': 'preprints',
                    'id': reviewable_id
                }
            }
        return payload

    def setUp(self):
        super(TestReviewLogCreate, self).setUp()

        self.url = '/{}reviews/review_logs/'.format(API_BASE)

        self.node_admin = AuthUserFactory()
        self.preprint = PreprintFactory(provider__reviews_workflow='pre-moderation', node__creator=self.node_admin)
        self.preprint.node.add_contributor(self.node_admin, permissions=[osf_permissions.ADMIN])
        self.moderator = AuthUserFactory()
        self.moderator.groups.add(GroupHelper(self.preprint.provider).get_group('moderator'))

    def test_create_permissions(self):
        assert self.preprint.reviews_state == 'initial'

        submit_payload = self.create_payload(self.preprint._id, action='submit')

        # Unauthorized user can't do anything
        res = self.app.post_json_api(self.url, submit_payload, expect_errors=True)
        assert res.status_code == 401

        # Node admin can submit
        res = self.app.post_json_api(self.url, submit_payload, auth=self.node_admin.auth)
        assert res.status_code == 201
        self.preprint.refresh_from_db()
        assert self.preprint.reviews_state == 'pending'
        assert not self.preprint.is_published

        accept_payload = self.create_payload(self.preprint._id, action='accept', comment='This is good.')

        # Unauthorized user can't do anything
        res = self.app.post_json_api(self.url, accept_payload, expect_errors=True)
        assert res.status_code == 401

        # Non-moderator can't accept
        some_rando = AuthUserFactory()
        res = self.app.post_json_api(self.url, accept_payload, auth=some_rando.auth, expect_errors=True)
        assert res.status_code == 403

        # Moderator from another provider can't accept
        another_moderator = AuthUserFactory()
        another_moderator.groups.add(GroupHelper(PreprintProviderFactory()).get_group('moderator'))

        # Node admin can't accept
        res = self.app.post_json_api(self.url, accept_payload, auth=self.node_admin.auth, expect_errors=True)
        assert res.status_code == 403

        # Moderator can accept
        res = self.app.post_json_api(self.url, accept_payload, auth=self.moderator.auth)
        assert res.status_code == 201
        self.preprint.refresh_from_db()
        assert self.preprint.reviews_state == 'accepted'
        assert self.preprint.is_published

    def test_cannot_create_review_logs_for_unmoderated_provider(self):
        self.preprint.provider.reviews_workflow = None
        self.preprint.provider.save()
        submit_payload = self.create_payload(self.preprint._id, action='submit')
        res = self.app.post_json_api(self.url, submit_payload, auth=self.node_admin.auth, expect_errors=True)
        assert res.status_code == 409

    def test_bad_requests(self):
        invalid_transitions = {
            'post-moderation': [
                ('accepted', 'accept'),
                ('accepted', 'submit'),
                ('initial', 'accept'),
                ('initial', 'edit_comment'),
                ('initial', 'reject'),
                ('pending', 'submit'),
                ('rejected', 'reject'),
                ('rejected', 'submit'),
            ],
            'pre-moderation': [
                ('accepted', 'accept'),
                ('accepted', 'submit'),
                ('initial', 'accept'),
                ('initial', 'edit_comment'),
                ('initial', 'reject'),
                ('rejected', 'reject'),
            ]
        }
        for workflow, transitions in invalid_transitions.items():
            self.preprint.provider.reviews_workflow = workflow
            self.preprint.provider.save()
            for state, action in transitions:
                self.preprint.reviews_state = state
                self.preprint.save()
                bad_payload = self.create_payload(self.preprint._id, action=action)
                res = self.app.post_json_api(self.url, bad_payload, auth=self.moderator.auth, expect_errors=True)
                assert res.status_code == 400

        # test reviewable is required
        bad_payload = self.create_payload(action='accept')
        res = self.app.post_json_api(self.url, bad_payload, auth=self.moderator.auth, expect_errors=True)
        assert res.status_code == 400

    def test_valid_transitions(self):
        valid_transitions = {
            'post-moderation': [
                ('accepted', 'edit_comment', 'accepted'),
                ('accepted', 'reject', 'rejected'),
                ('initial', 'submit', 'pending'),
                ('pending', 'accept', 'accepted'),
                ('pending', 'edit_comment', 'pending'),
                ('pending', 'reject', 'rejected'),
                ('rejected', 'accept', 'accepted'),
                ('rejected', 'edit_comment', 'rejected'),
            ],
            'pre-moderation': [
                ('accepted', 'edit_comment', 'accepted'),
                ('accepted', 'reject', 'rejected'),
                ('initial', 'submit', 'pending'),
                ('pending', 'accept', 'accepted'),
                ('pending', 'edit_comment', 'pending'),
                ('pending', 'reject', 'rejected'),
                ('pending', 'submit', 'pending'),
                ('rejected', 'accept', 'accepted'),
                ('rejected', 'edit_comment', 'rejected'),
                ('rejected', 'submit', 'pending'),
            ],
        }
        for workflow, transitions in valid_transitions.items():
            self.preprint.provider.reviews_workflow = workflow
            self.preprint.provider.save()
            for from_state, action, to_state in transitions:
                self.preprint.reviews_state = from_state
                self.preprint.is_published = False
                self.preprint.date_published = None
                self.preprint.date_last_transitioned = None
                self.preprint.save()
                payload = self.create_payload(self.preprint._id, action=action)
                res = self.app.post_json_api(self.url, payload, auth=self.moderator.auth)
                assert res.status_code == 201

                log = self.preprint.review_logs.order_by('-date_created').first()
                assert log.action == action

                self.preprint.refresh_from_db()
                assert self.preprint.reviews_state == to_state
                if self.preprint.in_public_reviews_state:
                    assert self.preprint.is_published
                    assert self.preprint.date_published == log.date_created
                else:
                    assert not self.preprint.is_published
                    assert self.preprint.date_published is None

                if action == 'edit_comment':
                    assert self.preprint.date_last_transitioned is None
                else:
                    assert self.preprint.date_last_transitioned == log.date_created
