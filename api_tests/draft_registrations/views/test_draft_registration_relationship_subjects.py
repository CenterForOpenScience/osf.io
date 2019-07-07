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
