import pytest

from api.base.settings.defaults import API_BASE
from api.preprint_providers.permissions import GroupHelper
from osf_tests.factories import (
    AuthUserFactory,
)
from website.util import permissions as osf_permissions

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
            user.groups.add(GroupHelper(preprint.provider).get_group('moderator'))
        else:
            preprint.node.add_contributor(user, permissions=[osf_permissions.READ, osf_permissions.WRITE, osf_permissions.ADMIN])
        return user

    @pytest.fixture()
    def expected_actions(self, preprint, all_actions):
        return [r for r in all_actions if r.target_id == preprint.id]

    @pytest.fixture()
    def url(self, preprint):
        return '/{}preprints/{}/actions/'.format(API_BASE, preprint._id)

    def test_unauthorized_user(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        user = AuthUserFactory()
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403


class TestReviewActionSettings(ReviewActionCommentSettingsMixin):
    @pytest.fixture()
    def url(self, preprint):
        return '/{}preprints/{}/actions/'.format(API_BASE, preprint._id)
