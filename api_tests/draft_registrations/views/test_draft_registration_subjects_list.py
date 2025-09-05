import pytest

from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsListMixin
from osf.utils.permissions import WRITE, READ
from osf_tests.factories import (
    DraftRegistrationFactory,
)
from tests.utils import capture_notifications


class TestDraftRegistrationSubjectsList(SubjectsListMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        # Overrides SubjectsListMixin
        with capture_notifications():
            draft = DraftRegistrationFactory(initiator=user_admin_contrib)
        draft.add_contributor(user_write_contrib, permissions=WRITE)
        draft.add_contributor(user_read_contrib, permissions=READ)
        draft.save()
        return draft

    @pytest.fixture()
    def url(self, resource):
        # Overrides SubjectsListMixin
        return f'/{API_BASE}draft_registrations/{resource._id}/subjects/'
