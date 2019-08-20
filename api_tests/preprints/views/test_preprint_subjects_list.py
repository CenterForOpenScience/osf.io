import pytest

from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsListMixin
from osf_tests.factories import (
    PreprintFactory,
)
from osf.utils.permissions import WRITE, READ


class TestPreprintSubjectsList(SubjectsListMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        # unpublished preprint in initial state - only creator can view
        preprint = PreprintFactory(creator=user_admin_contrib, is_published=False)
        preprint.subjects.clear()
        preprint.add_contributor(user_write_contrib, permissions=WRITE)
        preprint.add_contributor(user_read_contrib, permissions=READ)
        preprint.save()
        return preprint

    @pytest.fixture()
    def url(self, resource):
        return '/{}preprints/{}/subjects/'.format(API_BASE, resource._id)

    def test_get_resource_subjects_permissions(self, app, user_write_contrib,
            user_read_contrib, user_non_contrib, resource, url):
        # test_unauthorized
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # test_noncontrib
        res = app. get(url, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_read_contrib
        res = app. get(url, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_write_contrib
        res = app. get(url, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403
