import pytest

from osf.models import PreprintService
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory

@pytest.mark.django_db
class TestReviewable:

    def test_state_changes(self):
        user = AuthUserFactory()
        preprint = PreprintFactory(provider__reviews_workflow='pre-moderation', is_published=False)
        assert preprint.reviews_state == DefaultStates.INITIAL.value

        preprint.reviews_submit(user)
        assert preprint.reviews_state == DefaultStates.PENDING.value

        preprint.reviews_accept(user, 'comment')
        assert preprint.reviews_state == DefaultStates.ACCEPTED.value
        from_db = PreprintService.objects.get(id=preprint.id)
        assert from_db.reviews_state == DefaultStates.ACCEPTED.value

        preprint.reviews_reject(user, 'comment')
        assert preprint.reviews_state == DefaultStates.REJECTED.value
        from_db.refresh_from_db()
        assert from_db.reviews_state == DefaultStates.REJECTED.value

        preprint.reviews_accept(user, 'comment')
        assert preprint.reviews_state == DefaultStates.ACCEPTED.value
        from_db.refresh_from_db()
        assert from_db.reviews_state == DefaultStates.ACCEPTED.value
