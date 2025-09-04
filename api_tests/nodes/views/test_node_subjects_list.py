import pytest

from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsListMixin
from osf.utils.permissions import WRITE, READ
from osf_tests.factories import (
    ProjectFactory,
)

class TestNodeSubjectsList(SubjectsListMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        project = ProjectFactory(is_public=False, creator=user_admin_contrib)
        project.add_contributor(user_write_contrib, permissions=WRITE)
        project.add_contributor(user_read_contrib, permissions=READ)
        project.save()
        return project

    @pytest.fixture()
    def url(self, resource):
        return f'/{API_BASE}nodes/{resource._id}/subjects/'
