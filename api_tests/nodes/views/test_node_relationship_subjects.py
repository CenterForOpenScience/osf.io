import pytest
from waffle.testutils import override_flag

from osf.utils.permissions import WRITE, READ
from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsRelationshipMixin
from osf import features
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    SubjectFactory,
)


@pytest.mark.django_db
class TestNodeRelationshipSubjects(SubjectsRelationshipMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        project = ProjectFactory(is_public=False, creator=user_admin_contrib)
        project.add_contributor(user_write_contrib, permissions=WRITE)
        project.add_contributor(user_read_contrib, permissions=READ)
        project.save()
        return project

    @pytest.fixture()
    def url(self, resource):
        return f'/{API_BASE}nodes/{resource._id}/relationships/subjects/'


@pytest.mark.django_db
class TestNodeSubjectsRelationshipProjectReadOnly:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def url(self, node):
        return f'/{API_BASE}nodes/{node._id}/relationships/subjects/'

    @pytest.fixture()
    def payload(self, subject):
        return {'data': [{'type': 'subjects', 'id': subject._id}]}

    def test_put_blocked_when_project_read_only_flag_active(self, app, user, url, payload):
        with override_flag(features.PROJECT_READ_ONLY, active=True):
            res = app.put_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 405
        assert res.json['errors'][0]['detail'] == 'This action is no longer available. Contact support if you have any questions.'

    def test_patch_blocked_when_project_read_only_flag_active(self, app, user, url, payload):
        with override_flag(features.PROJECT_READ_ONLY, active=True):
            res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 405
        assert res.json['errors'][0]['detail'] == 'This action is no longer available. Contact support if you have any questions.'

    def test_patch_allowed_when_project_read_only_flag_inactive(self, app, user, node, subject, url, payload):
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert subject in node.subjects.all()
