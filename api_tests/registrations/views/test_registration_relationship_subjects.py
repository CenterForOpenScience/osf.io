import pytest

from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsRelationshipMixin
from osf_tests.factories import (
    RegistrationFactory
)
from osf.utils.permissions import WRITE, READ


@pytest.mark.django_db
class TestRegistrationRelationshipSubjects(SubjectsRelationshipMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        registration = RegistrationFactory(is_public=False, creator=user_admin_contrib)
        registration.add_contributor(user_write_contrib, permissions=WRITE)
        registration.add_contributor(user_read_contrib, permissions=READ)
        registration.save()
        return registration

    @pytest.fixture()
    def url(self, resource):
        return f'/{API_BASE}registrations/{resource._id}/relationships/subjects/'

    def test_update_subjects_empty_payload(self, app, user_admin_contrib, resource, url, subject):
        # override test as registration must have at least one subject to be registered
        resource.subjects.add(subject)

        payload = {
            'data': []
        }

        res = app.patch_json_api(url, payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registration must have at least one subject to be registered'
        assert resource.subjects.count() == 1
