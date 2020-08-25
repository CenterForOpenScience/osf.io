import pytest

from api.base.settings.defaults import API_BASE
from api_tests.subjects.mixins import SubjectsListMixin
from osf.utils.permissions import WRITE, READ
from osf_tests.factories import (
    DraftRegistrationFactory,
)

class TestDraftRegistrationSubjectsList(SubjectsListMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        # Overrides SubjectsListMixin
        draft = DraftRegistrationFactory(initiator=user_admin_contrib)
        draft.add_contributor(user_write_contrib, permissions=WRITE)
        draft.add_contributor(user_read_contrib, permissions=READ)
        draft.save()
        return draft

    @pytest.fixture()
    def url(self, resource):
        # Overrides SubjectsListMixin
        return '/{}draft_registrations/{}/subjects/'.format(API_BASE, resource._id)
