from unittest import mock
from datetime import timedelta

from django.utils import timezone

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory

from scripts.triggered_mails import main, find_inactive_users_without_enqueued_or_sent_no_login, NO_LOGIN_PREFIX, send_no_login_email
import uuid
from osf.models import EmailTask
from tests.utils import capture_notifications


class TestTriggeredMails(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.user.date_last_login = timezone.now()
        self.user.save()

    def test_dont_trigger_no_login_mail(self):
        self.user.date_last_login = timezone.now() - timedelta(seconds=6)
        self.user.save()
        with capture_notifications(expect_none=True):
            main(dry_run=False)

    def test_trigger_no_login_mail(self):
        self.user.date_last_login = timezone.now() - timedelta(weeks=6)
        self.user.save()
        assert len(find_inactive_users_without_enqueued_or_sent_no_login()) == 1
        main(dry_run=False)
        assert len(find_inactive_users_without_enqueued_or_sent_no_login()) == 0

    def test_find_inactive_users_with_no_inactivity_email_sent_or_queued(self):
        user_active = UserFactory(fullname='Spot')
        user_inactive = UserFactory(fullname='Nucha')
        user_already_received_mail = UserFactory(fullname='Pep')
        user_active.date_last_login = timezone.now() - timedelta(seconds=6)
        user_inactive.date_last_login = timezone.now() - timedelta(weeks=6)
        user_already_received_mail.date_last_login = timezone.now() - timedelta(weeks=6)
        user_active.save()
        user_inactive.save()
        user_already_received_mail.save()
        task_id = f'{NO_LOGIN_PREFIX}{uuid.uuid4()}'
        email_task = EmailTask.objects.create(
            task_id=task_id,
            user=user_already_received_mail,
            status='PENDING',
        )

        send_no_login_email.delay(email_task_id=email_task.id)

        users = find_inactive_users_without_enqueued_or_sent_no_login()
        assert len(users) == 1
