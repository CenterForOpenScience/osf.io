import mock
import pytest

from osf.models import Preprint
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory

@pytest.mark.django_db
class TestReviewable:

    @mock.patch('website.identifiers.utils.request_identifiers')
    def test_state_changes(self, _):
        user = AuthUserFactory()
        preprint = PreprintFactory(reviews_workflow='pre-moderation', is_published=False)
        assert preprint.machine_state == DefaultStates.INITIAL.value

        preprint.run_submit(user)
        assert preprint.machine_state == DefaultStates.PENDING.value

        preprint.run_accept(user, 'comment')
        assert preprint.machine_state == DefaultStates.ACCEPTED.value
        from_db = Preprint.objects.get(id=preprint.id)
        assert from_db.machine_state == DefaultStates.ACCEPTED.value

        preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value
        from_db.refresh_from_db()
        assert from_db.machine_state == DefaultStates.REJECTED.value

        preprint.run_accept(user, 'comment')
        assert preprint.machine_state == DefaultStates.ACCEPTED.value
        from_db.refresh_from_db()
        assert from_db.machine_state == DefaultStates.ACCEPTED.value
