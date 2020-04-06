import pytest

from osf.utils.permissions import WRITE, READ
from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsRelationshipMixin
from osf_tests.factories import (
    DraftRegistrationFactory
)


@pytest.mark.django_db
class TestDraftRegistrationRelationshipSubjects(SubjectsRelationshipMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        draft = DraftRegistrationFactory(creator=user_admin_contrib)
        draft.add_contributor(user_write_contrib, permissions=WRITE)
        draft.add_contributor(user_read_contrib, permissions=READ)
        draft.save()
        return draft

    @pytest.fixture()
    def url(self, resource):
        return '/{}draft_registrations/{}/relationships/subjects/'.format(API_BASE, resource._id)

    # Overwrites SubjectsRelationshipMixin
    def test_update_subjects_relationship_permissions(self, app, user_write_contrib,
            user_read_contrib, user_non_contrib, resource, url, payload):
        # test_unauthorized
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # test_noncontrib
        res = app.patch_json_api(url, payload, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_write_contrib
        res = app.patch_json_api(url, payload, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 200

        # test_read_contrib
        res = app.patch_json_api(url, payload, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403
