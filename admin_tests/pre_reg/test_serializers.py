import pytest

from osf_tests.factories import DraftRegistrationFactory, ProjectFactory, AuthUserFactory, RegistrationFactory, RetractionFactory
from osf.models import DraftRegistrationApproval
from website.prereg.utils import get_prereg_schema
from admin.pre_reg.serializers import get_approval_status

pytestmark = pytest.mark.django_db

class TestGetApprovalStatus:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def draft_pending_approval(self, user):
        return DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())

    @pytest.fixture()
    def draft_approved_and_registered(self, user, project):
        draft = DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())
        draft.approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        draft.approval.state = 'approved'
        draft.approval.save()
        draft.registered_node = RegistrationFactory(creator=user, project=project, is_public=True)
        draft.save()
        return draft

    @pytest.fixture()
    def draft_approved_but_canceled(self, user, project):
        draft = DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())
        draft.registered_node = RegistrationFactory(creator=user, project=project, is_public=True)
        draft.registered_node.is_deleted = True
        draft.registered_node.save()
        draft.save()
        return draft

    @pytest.fixture()
    def draft_approved_but_withdrawn(self, user, project):
        draft = DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())
        draft.registered_node = RegistrationFactory(creator=user, project=project, is_public=True, retraction=RetractionFactory())
        draft.save()
        return draft

    @pytest.fixture()
    def draft_approved_but_not_registered(self, user, project):
        draft = DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())
        draft.approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        draft.approval.state = 'approved'
        draft.approval.save()
        draft.save()
        return draft

    @pytest.fixture()
    def draft_rejected(self, user, project):
        draft = DraftRegistrationFactory(initiator=user, registration_schema=get_prereg_schema())
        draft.approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        draft.approval.state = 'rejected'
        draft.approval.save()
        draft.save()
        return draft

    def test_draft_pending_approval(self, draft_pending_approval):
        assert get_approval_status(draft_pending_approval) == 'Pending approval'

    def test_draft_approved_and_registered(self, draft_approved_and_registered):
        assert get_approval_status(draft_approved_and_registered) == 'Approved and registered'

    def test_draft_approved_but_canceled(self, draft_approved_but_canceled):
        assert get_approval_status(draft_approved_but_canceled) == 'Approved but canceled'

    def test_draft_approved_but_withdrawn(self, draft_approved_but_withdrawn):
        assert get_approval_status(draft_approved_but_withdrawn) == 'Approved but withdrawn'

    def test_draft_approved_but_not_registered(self, draft_approved_but_not_registered):
        assert get_approval_status(draft_approved_but_not_registered) == 'Approved but not registered'

    def test_draft_rejected(self, draft_rejected):
        assert get_approval_status(draft_rejected) == 'Rejected'
