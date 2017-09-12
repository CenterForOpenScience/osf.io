import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
)
from reviews.permissions import GroupHelper
from website.util import permissions as osf_permissions

from api_tests.reviews.mixins.filter_mixins import ReviewLogFilterMixin
from api_tests.reviews.mixins.comment_settings import ReviewLogCommentSettingsMixin


class TestPreprintReviewLogFilters(ReviewLogFilterMixin):

    @pytest.fixture()
    def preprint(self, all_review_logs):
        return all_review_logs[0].reviewable

    @pytest.fixture()
    @pytest.mark.parametrize('moderator', [True, False])
    def user(self, preprint, moderator):
        user = AuthUserFactory()
        if moderator:
            user.groups.add(GroupHelper(preprint.provider).get_group('moderator'))
        else:
            preprint.node.add_contributor(user, permissions=[osf_permissions.READ, osf_permissions.WRITE, osf_permissions.ADMIN])
        return user

    @pytest.fixture()
    def expected_logs(self, preprint, all_review_logs):
        return [r for r in all_review_logs if r.reviewable_id == preprint.id]

    @pytest.fixture()
    def url(self, preprint):
        return '/{}preprints/{}/review_logs/'.format(API_BASE, preprint._id)

    def test_unauthorized_user(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        user = AuthUserFactory()
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403


class TestReviewLogSettings(ReviewLogCommentSettingsMixin):
    @pytest.fixture()
    def url(self, preprint):
        return '/{}preprints/{}/review_logs/'.format(API_BASE, preprint._id)
