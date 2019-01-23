import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    PreprintProviderFactory,
)
from osf.utils import permissions as osf_permissions


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestReviewActionCreateRoot(object):
    def create_payload(self, reviewable_id=None, **attrs):
        payload = {
            'data': {
                'attributes': attrs,
                'relationships': {},
                'type': 'actions'
            }
        }
        if reviewable_id:
            payload['data']['relationships']['target'] = {
                'data': {
                    'type': 'preprints',
                    'id': reviewable_id
                }
            }
        return payload

    @pytest.fixture()
    def url(self, preprint):
        return '/{}actions/reviews/'.format(API_BASE)

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory(reviews_workflow='pre-moderation')

    @pytest.fixture()
    def node_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, node_admin, provider):
        preprint = PreprintFactory(
            provider=provider,
            is_published=False
        )
        preprint.add_contributor(
            node_admin, permissions=osf_permissions.ADMIN
        )
        return preprint

    @pytest.fixture()
    def moderator(self, provider):
        moderator = AuthUserFactory()
        moderator.groups.add(provider.get_group('moderator'))
        return moderator

    def test_create_permissions(
            self, app, url, preprint, node_admin, moderator
    ):
        assert preprint.machine_state == 'initial'

        submit_payload = self.create_payload(preprint._id, trigger='submit')

        # Unauthorized user can't submit
        res = app.post_json_api(url, submit_payload, expect_errors=True)
        assert res.status_code == 401

        # A random user can't submit
        some_rando = AuthUserFactory()
        res = app.post_json_api(
            url, submit_payload,
            auth=some_rando.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # Node admin can submit
        res = app.post_json_api(url, submit_payload, auth=node_admin.auth)
        assert res.status_code == 201
        preprint.refresh_from_db()
        assert preprint.machine_state == 'pending'
        assert not preprint.is_published

        accept_payload = self.create_payload(
            preprint._id, trigger='accept', comment='This is good.'
        )

        # Unauthorized user can't accept
        res = app.post_json_api(url, accept_payload, expect_errors=True)
        assert res.status_code == 401

        # A random user can't accept
        res = app.post_json_api(
            url, accept_payload,
            auth=some_rando.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # Moderator from another provider can't accept
        another_moderator = AuthUserFactory()
        another_moderator.groups.add(
            PreprintProviderFactory().get_group('moderator')
        )
        res = app.post_json_api(
            url, accept_payload,
            auth=another_moderator.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # Node admin can't accept
        res = app.post_json_api(
            url, accept_payload,
            auth=node_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # Still unchanged after all those tries
        preprint.refresh_from_db()
        assert preprint.machine_state == 'pending'
        assert not preprint.is_published

        # Moderator can accept
        res = app.post_json_api(url, accept_payload, auth=moderator.auth)
        assert res.status_code == 201
        preprint.refresh_from_db()
        assert preprint.machine_state == 'accepted'
        assert preprint.is_published

    def test_cannot_create_actions_for_unmoderated_provider(
            self, app, url, preprint, provider, node_admin
    ):
        provider.reviews_workflow = None
        provider.save()
        submit_payload = self.create_payload(preprint._id, trigger='submit')
        res = app.post_json_api(
            url, submit_payload,
            auth=node_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_bad_requests(self, app, url, preprint, provider, moderator):
        invalid_transitions = {
            'post-moderation': [
                ('accepted', 'accept'),
                ('accepted', 'submit'),
                ('initial', 'accept'),
                ('initial', 'edit_comment'),
                ('initial', 'reject'),
                ('initial', 'withdraw'),
                ('pending', 'submit'),
                ('rejected', 'reject'),
                ('rejected', 'submit'),
                ('rejected', 'withdraw'),
                ('withdrawn', 'submit'),
                ('withdrawn', 'accept'),
                ('withdrawn', 'reject'),
                ('withdrawn', 'edit_comment'),
                ('withdrawn', 'withdraw'),
            ],
            'pre-moderation': [
                ('accepted', 'accept'),
                ('accepted', 'submit'),
                ('initial', 'accept'),
                ('initial', 'edit_comment'),
                ('initial', 'reject'),
                ('initial', 'withdraw'),
                ('rejected', 'reject'),
                ('rejected', 'withdraw'),
                ('withdrawn', 'submit'),
                ('withdrawn', 'accept'),
                ('withdrawn', 'reject'),
                ('withdrawn', 'edit_comment'),
                ('withdrawn', 'withdraw'),
            ]
        }
        for workflow, transitions in invalid_transitions.items():
            provider.reviews_workflow = workflow
            provider.save()
            for state, trigger in transitions:
                preprint.machine_state = state
                preprint.save()
                bad_payload = self.create_payload(
                    preprint._id, trigger=trigger
                )
                res = app.post_json_api(
                    url, bad_payload,
                    auth=moderator.auth, expect_errors=True
                )
                assert res.status_code == 409

        # test invalid trigger
        bad_payload = self.create_payload(
            preprint._id, trigger='badtriggerbad'
        )
        res = app.post_json_api(
            url, bad_payload,
            auth=moderator.auth,
            expect_errors=True
        )
        assert res.status_code == 400

        # test target is required
        bad_payload = self.create_payload(trigger='accept')
        res = app.post_json_api(
            url, bad_payload,
            auth=moderator.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    def test_valid_transitions(
            self, app, url, preprint, provider, moderator
    ):
        valid_transitions = {
            'post-moderation': [
                ('accepted', 'edit_comment', 'accepted'),
                ('accepted', 'reject', 'rejected'),
                ('accepted', 'withdraw', 'withdrawn'),
                ('initial', 'submit', 'pending'),
                ('pending', 'accept', 'accepted'),
                ('pending', 'edit_comment', 'pending'),
                ('pending', 'reject', 'rejected'),
                ('pending', 'withdraw', 'withdrawn'),
                ('rejected', 'accept', 'accepted'),
                ('rejected', 'edit_comment', 'rejected'),
            ],
            'pre-moderation': [
                ('accepted', 'edit_comment', 'accepted'),
                ('accepted', 'reject', 'rejected'),
                ('accepted', 'withdraw', 'withdrawn'),
                ('initial', 'submit', 'pending'),
                ('pending', 'accept', 'accepted'),
                ('pending', 'edit_comment', 'pending'),
                ('pending', 'reject', 'rejected'),
                ('pending', 'submit', 'pending'),
                ('pending', 'withdraw', 'withdrawn'),
                ('rejected', 'accept', 'accepted'),
                ('rejected', 'edit_comment', 'rejected'),
                ('rejected', 'submit', 'pending'),
            ],
        }
        for workflow, transitions in list(valid_transitions.items()):
            provider.reviews_workflow = workflow
            provider.save()
            for from_state, trigger, to_state in transitions:
                preprint.machine_state = from_state
                preprint.is_published = False
                preprint.date_published = None
                preprint.date_withdrawn = None
                preprint.date_last_transitioned = None
                preprint.save()
                payload = self.create_payload(preprint._id, trigger=trigger)
                res = app.post_json_api(url, payload, auth=moderator.auth)
                assert res.status_code == 201

                action = preprint.actions.order_by('-created').first()
                assert action.trigger == trigger

                preprint.refresh_from_db()
                assert preprint.machine_state == to_state
                if preprint.in_public_reviews_state:
                    assert preprint.is_published
                    assert preprint.date_published == action.created
                else:
                    assert not preprint.is_published
                    assert preprint.date_published is None

                if trigger == 'edit_comment':
                    assert preprint.date_last_transitioned is None
                else:
                    assert preprint.date_last_transitioned == action.created
