import pytest

from osf.management.commands.update_old_sanction_states import update_old_sanction_states
from osf.models import Embargo, Retraction
from osf_tests import factories

@pytest.mark.django_db
class TestUpdateOldSanctionStates:

    def test_update_old_sanction_states(self):
        new_style_embargo = factories.EmbargoFactory()
        old_style_embargo = factories.EmbargoFactory()
        old_style_embargo.state = 'active'
        old_style_embargo.save()
        old_style_cancelled_embargo = factories.EmbargoFactory()
        old_style_cancelled_embargo.state = 'cancelled'
        old_style_cancelled_embargo.save()

        new_style_retraction = factories.RetractionFactory()
        old_style_retraction = factories.RetractionFactory()
        old_style_retraction.state = 'retracted'
        old_style_retraction.save()
        old_style_cancelled_retraction = factories.RetractionFactory()
        old_style_cancelled_retraction.state = 'cancelled'
        old_style_cancelled_retraction.save()
        old_style_pending_retraction = factories.RetractionFactory()
        old_style_pending_retraction.state = 'pending'
        old_style_pending_retraction.save()

        assert Embargo.objects.filter(state=Embargo.UNAPPROVED).count() == 1
        assert Embargo.objects.filter(state=Embargo.APPROVED).count() == 0
        assert Embargo.objects.filter(state=Embargo.REJECTED).count() == 0
        assert Retraction.objects.filter(state=Retraction.UNAPPROVED).count() == 1
        assert Retraction.objects.filter(state=Retraction.APPROVED).count() == 0
        assert Retraction.objects.filter(state=Retraction.REJECTED).count() == 0

        update_old_sanction_states()

        assert Embargo.objects.filter(state=Embargo.UNAPPROVED).count() == 1
        assert Embargo.objects.filter(state=Embargo.APPROVED).count() == 1
        assert Embargo.objects.filter(state=Embargo.REJECTED).count() == 1
        assert Retraction.objects.filter(state=Retraction.UNAPPROVED).count() == 2
        assert Retraction.objects.filter(state=Retraction.APPROVED).count() == 1
        assert Retraction.objects.filter(state=Retraction.REJECTED).count() == 1

        new_style_embargo.refresh_from_db()
        assert new_style_embargo.state == Embargo.UNAPPROVED
        new_style_retraction.refresh_from_db()
        assert new_style_retraction.state == Retraction.UNAPPROVED
        old_style_embargo.refresh_from_db()
        assert old_style_embargo.state == Embargo.APPROVED
        old_style_retraction.refresh_from_db()
        assert old_style_retraction.state == Retraction.APPROVED
        old_style_pending_retraction.refresh_from_db()
        assert old_style_pending_retraction.state == Retraction.UNAPPROVED
        old_style_cancelled_embargo.refresh_from_db()
        assert old_style_cancelled_embargo.state == Embargo.REJECTED
        old_style_cancelled_retraction.refresh_from_db()
        assert old_style_cancelled_retraction.state == Retraction.REJECTED
