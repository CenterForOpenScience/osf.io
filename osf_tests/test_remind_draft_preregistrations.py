import pytest
from django.utils import timezone
from website import settings

from .factories import UserFactory, DraftRegistrationFactory

from osf.models import MetaSchema, DraftRegistrationApproval, QueuedMail
from osf.models.queued_mail import PREREG_REMINDER_TYPE

from scripts.remind_draft_preregistrations import main

@pytest.fixture()
def user():
    return UserFactory(is_registered=True)

@pytest.fixture()
def schema():
    return MetaSchema.objects.get(name='Prereg Challenge')

@pytest.mark.django_db
class TestPreregReminder:

    @pytest.fixture()
    def draft(self, user, schema):
        draft = DraftRegistrationFactory(
            registration_schema=schema, initiator=user
        )
        draft.datetime_initiated = timezone.now() - settings.PREREG_WAIT_TIME
        draft.save()
        return draft


    def test_trigger_prereg_reminder(self, draft):
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 1

    def test_dont_trigger_prereg_reminder_too_new(self, schema):
        DraftRegistrationFactory(registration_schema=schema)
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 0

    def test_dont_trigger_prereg_reminder_too_old(self, draft):
        draft.datetime_initiated = timezone.now() - settings.PREREG_AGE_LIMIT
        draft.save()
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 0

    def test_dont_trigger_prereg_reminder_not_prereg(self):
        DraftRegistrationFactory(datetime_initiated = timezone.now() - settings.PREREG_WAIT_TIME)
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 0

    def test_dont_trigger_prereg_reminder_already_sent(self, draft):
        draft.reminder_sent = True
        draft.save()
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 0

    def test_dont_trigger_prereg_reminder_draft_submitted(self, draft):
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        approval.save()
        draft.approval = approval
        draft.save()
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 0

    def test_dont_trigger_prereg_reminder_wrong_schema(self):
        draft = DraftRegistrationFactory()
        draft.datetime_initiated = timezone.now() - settings.PREREG_WAIT_TIME
        draft.save()
        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == 0


    def test_dont_trigger_prereg_reminder_hit_user_max(self, schema, user):
        for i in range(settings.MAX_PREREG_REMINDER_EMAILS + 1):
            temp_draft = DraftRegistrationFactory(initiator=user, registration_schema=schema)
            temp_draft.datetime_initiated = timezone.now() - settings.PREREG_WAIT_TIME
            temp_draft.save()

        main(dry_run=False)

        assert len(QueuedMail.objects.filter(email_type=PREREG_REMINDER_TYPE)) == settings.MAX_PREREG_REMINDER_EMAILS
