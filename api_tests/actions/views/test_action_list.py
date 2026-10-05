import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NotificationTypeEnum
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    PreprintProviderFactory,
)
from osf.utils import permissions as osf_permissions
from tests.utils import capture_notifications
from website.settings import OSF_ADMIN_URL, OSF_SUPPORT_EMAIL


@pytest.mark.django_db
class TestReviewActionCreateRoot:
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
        return f'/{API_BASE}actions/reviews/'

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

    def test_create_permissions_unauthorized(self, app, url, preprint, node_admin, moderator):
        assert preprint.machine_state == 'initial'

        submit_payload = self.create_payload(
            preprint._id,
            trigger='submit'
        )

        # Unauthorized user can't submit
        res = app.post_json_api(
            url,
            submit_payload,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_create_permissions_forbidden(self, app, url, preprint, node_admin, moderator):
        assert preprint.machine_state == 'initial'

        submit_payload = self.create_payload(
            preprint._id,
            trigger='submit'
        )

        # A random user can't submit
        some_rando = AuthUserFactory()
        res = app.post_json_api(
            url,
            submit_payload,
            auth=some_rando.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_create_permissions_success(self, app, url, preprint, node_admin, moderator):
        assert preprint.machine_state == 'initial'

        submit_payload = self.create_payload(
            preprint._id,
            trigger='submit'
        )

        # Node admin can submit
        with capture_notifications():
            res = app.post_json_api(
                url,
                submit_payload,
                auth=node_admin.auth
            )
        assert res.status_code == 201
        preprint.refresh_from_db()
        assert preprint.machine_state == 'pending'
        assert not preprint.is_published

    def test_accept_permissions_unauthorized(self, app, url, preprint, node_admin, moderator):
        preprint.machine_state = 'pending'
        preprint.save()
        assert preprint.machine_state == 'pending'

        accept_payload = self.create_payload(
            preprint._id,
            trigger='accept',
            comment='This is good.'
        )

        # Unauthorized user can't accept
        res = app.post_json_api(url, accept_payload, expect_errors=True)
        assert res.status_code == 401

    def test_accept_permissions_forbidden(self, app, url, preprint, node_admin, moderator):
        preprint.machine_state = 'pending'
        preprint.save()
        assert preprint.machine_state == 'pending'

        accept_payload = self.create_payload(
            preprint._id,
            trigger='accept',
            comment='This is good.'
        )

        some_rando = AuthUserFactory()

        # A random user can't accept
        res = app.post_json_api(
            url,
            accept_payload,
            auth=some_rando.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_accept_permissions_other_mod(self, app, url, preprint, node_admin, moderator):
        another_moderator = AuthUserFactory()
        another_moderator.groups.add(
            PreprintProviderFactory().get_group('moderator')
        )
        accept_payload = self.create_payload(
            preprint._id,
            trigger='accept',
            comment='This is good.'
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

    def test_accept_permissions_accept(self, app, url, preprint, node_admin, moderator):
        preprint.machine_state = 'pending'
        preprint.save()
        accept_payload = self.create_payload(
            preprint._id,
            trigger='accept',
            comment='This is good.'
        )

        # Still unchanged after all those tries
        preprint.refresh_from_db()
        assert preprint.machine_state == 'pending'
        assert not preprint.is_published

        # Moderator can accept
        with capture_notifications() as notifications:
            res = app.post_json_api(url, accept_payload, auth=moderator.auth)
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS
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
                with capture_notifications(allow_none=True):  # covers cases where notification are sent and not sent.
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

    def test_invalid_target_id(self, app, moderator):
        """
        This test simulates the issue reported where using either an invalid
        action ID or an unrelated node ID as the target ID results in a 502 error.

        It attempts to create a review action with a bad `target.id`.
        """
        res = app.post_json_api(
            f'/{API_BASE}actions/reviews/',
            {
                'data': {
                    'type': 'actions',
                    'attributes': {
                        'trigger': 'submit'
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': 'preprints',
                                'id': 'deadbeef1234'
                            }
                        }
                    }
                }
            },
            auth=moderator.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_submit_preprint_without_files_returns_400(self, app, url, preprint, node_admin):
        # Ensure preprint has no files
        preprint.primary_file = None
        preprint.save()

        submit_payload = self.create_payload(
            preprint._id,
            trigger='submit'
        )

        res = app.post_json_api(
            url,
            submit_payload,
            auth=node_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    def test_provider_not_reviewed_returns_409(self, app, url, preprint, node_admin):
        preprint.provider = PreprintProviderFactory(reviews_workflow=None)
        preprint.save()

        submit_payload = self.create_payload(
            preprint._id,
            trigger='submit'
        )

        res = app.post_json_api(
            url,
            submit_payload,
            auth=node_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_report_spam_permissions_unauthorized(self, app, url, preprint):
        preprint.machine_state = 'pending'
        preprint.save()
        res = app.post_json_api(
            url,
            self.create_payload(preprint._id, trigger='report_spam'),
            expect_errors=True
        )
        assert res.status_code == 401

    def test_report_spam_permissions_forbidden(self, app, url, preprint, node_admin):
        preprint.machine_state = 'pending'
        preprint.save()
        report_payload = self.create_payload(preprint._id, trigger='report_spam')
        # A random user can't report spam
        res = app.post_json_api(
            url,
            report_payload,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403
        # Neither can a moderator for a different provider
        another_moderator = AuthUserFactory()
        another_moderator.groups.add(
            PreprintProviderFactory().get_group('moderator')
        )
        res = app.post_json_api(
            url,
            report_payload,
            auth=another_moderator.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        res = app.post_json_api(
            url,
            report_payload,
            auth=node_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_report_spam_notifies_support(self, app, url, preprint, moderator):
        preprint.machine_state = 'pending'
        preprint.save()
        report_payload = self.create_payload(
            preprint._id,
            trigger='report_spam',
            comment='This is spam.'
        )
        with capture_notifications() as notifications:
            res = app.post_json_api(url, report_payload, auth=moderator.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['trigger'] == 'report_spam'
        assert res.json['data']['attributes']['from_state'] == 'pending'
        assert res.json['data']['attributes']['to_state'] == 'pending'
        assert len(notifications['emits']) == 1
        emit = notifications['emits'][0]
        assert emit['type'] == NotificationTypeEnum.DESK_MODERATOR_SPAM_REPORT
        assert emit['kwargs']['destination_address'] == OSF_SUPPORT_EMAIL
        assert emit['kwargs']['event_context']['moderator__id'] == moderator._id
        assert emit['kwargs']['event_context']['resource__id'] == preprint._id
        assert emit['kwargs']['event_context']['comment'] == 'This is spam.'
        context = emit['kwargs']['event_context']
        assert context['resource_creator__id'] == preprint.creator._id
        admin_app = OSF_ADMIN_URL.rstrip('/')
        assert context['creator_admin_app_url'] == (f'{admin_app}/users/{preprint.creator._id}/' if admin_app else '')
        assert context['resource_admin_app_url'] == (f'{admin_app}/preprints/{preprint._id}/' if admin_app else '')
        # report logged, preprint untouched
        preprint.refresh_from_db()
        assert preprint.machine_state == 'pending'
        assert preprint.spam_status is None
        assert preprint.actions.filter(trigger='report_spam').count() == 1

    def test_report_spam_invalid_state_returns_409(self, app, url, preprint, moderator):
        assert preprint.machine_state == 'initial'
        res = app.post_json_api(
            url,
            self.create_payload(preprint._id, trigger='report_spam'),
            auth=moderator.auth,
            expect_errors=True
        )
        assert res.status_code == 409
        assert not preprint.actions.filter(trigger='report_spam').exists()

    def test_report_spam_is_repeatable(self, app, url, preprint, moderator):
        preprint.machine_state = 'pending'
        preprint.save()
        report_payload = self.create_payload(preprint._id, trigger='report_spam')
        with capture_notifications() as notifications:
            assert app.post_json_api(url, report_payload, auth=moderator.auth).status_code == 201
            assert app.post_json_api(url, report_payload, auth=moderator.auth).status_code == 201
        assert len(notifications['emits']) == 2
        assert preprint.actions.filter(trigger='report_spam').count() == 2
