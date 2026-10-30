import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NotificationTypeEnum
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
)
from osf.utils import permissions as osf_permissions
from tests.utils import capture_notifications

from api_tests.reviews.mixins.filter_mixins import ReviewActionFilterMixin
from api_tests.reviews.mixins.comment_settings import ReviewActionCommentSettingsMixin


class TestPreprintActionFilters(ReviewActionFilterMixin):

    @pytest.fixture()
    def preprint(self, all_actions):
        return all_actions[0].target

    @pytest.fixture(params=[True, False], ids=['moderator', 'node_admin'])
    def user(self, request, preprint):
        user = AuthUserFactory()
        if request.param:
            user.groups.add(preprint.provider.get_group('moderator'))
        else:
            preprint.add_contributor(
                user,
                permissions=osf_permissions.ADMIN)
        return user

    @pytest.fixture()
    def expected_actions(self, preprint, all_actions):
        return [r for r in all_actions if r.target_id == preprint.id]

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/review_actions/'

    def test_unauthorized_user(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        user = AuthUserFactory()
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403


class TestReviewActionSettings(ReviewActionCommentSettingsMixin):
    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/review_actions/'


@pytest.mark.django_db
class TestPreprintActionReportSpam:

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory(reviews_workflow='pre-moderation')

    @pytest.fixture()
    def preprint(self, provider):
        preprint = PreprintFactory(provider=provider, is_published=False)
        preprint.machine_state = 'pending'
        preprint.save()
        return preprint

    @pytest.fixture()
    def moderator(self, provider):
        moderator = AuthUserFactory()
        moderator.groups.add(provider.get_group('moderator'))
        return moderator

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/review_actions/'

    @pytest.fixture()
    def payload(self, preprint):
        return {
            'data': {
                'type': 'actions',
                'attributes': {
                    'trigger': 'report_spam',
                    'comment': 'This is spam.'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'preprints',
                            'id': preprint._id
                        }
                    }
                }
            }
        }

    def test_moderator_can_report_spam(self, app, url, payload, preprint, moderator):
        with capture_notifications() as notifications:
            res = app.post_json_api(url, payload, auth=moderator.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['trigger'] == 'report_spam'
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.DESK_MODERATOR_SPAM_REPORT
        preprint.refresh_from_db()
        assert preprint.actions.filter(trigger='report_spam').exists()
        assert preprint.machine_state == 'pending'

    def test_non_moderator_cannot_report_spam(self, app, url, payload, preprint):
        node_admin = AuthUserFactory()
        preprint.add_contributor(node_admin, permissions=osf_permissions.ADMIN)
        res = app.post_json_api(url, payload, auth=node_admin.auth, expect_errors=True)
        assert res.status_code == 403
        assert not preprint.actions.filter(trigger='report_spam').exists()
