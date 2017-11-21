import pytest

from osf.models import PreprintService
from osf_tests.factories import PreprintFactory, AuthUserFactory
from reviews.workflow import States

@pytest.mark.django_db
class TestReviewable:

    def test_state_changes(self):
        user = AuthUserFactory()
        preprint = PreprintFactory(provider__reviews_workflow='pre-moderation', is_published=False)
        assert preprint.reviews_state == States.INITIAL.value

        preprint.reviews_submit(user)
        assert preprint.reviews_state == States.PENDING.value

        preprint.reviews_accept(user, 'comment')
        assert preprint.reviews_state == States.ACCEPTED.value
        from_db = PreprintService.objects.get(id=preprint.id)
        assert from_db.reviews_state == States.ACCEPTED.value

        preprint.reviews_reject(user, 'comment')
        assert preprint.reviews_state == States.REJECTED.value
        from_db.refresh_from_db()
        assert from_db.reviews_state == States.REJECTED.value

        preprint.reviews_accept(user, 'comment')
        assert preprint.reviews_state == States.ACCEPTED.value
        from_db.refresh_from_db()
        assert from_db.reviews_state == States.ACCEPTED.value
