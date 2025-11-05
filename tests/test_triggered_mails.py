# tests/test_triggered_mails.py
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from tests.base import OsfTestCase
from tests.utils import run_celery_tasks, capture_notifications

from osf_tests.factories import UserFactory
from osf.models import EmailTask, NotificationType

from scripts.triggered_mails import (
    find_inactive_users_without_enqueued_or_sent_no_login,
    main,
    NO_LOGIN_PREFIX,
)


def _inactive_time():
    """Make a timestamp that is definitely 'inactive' regardless of threshold settings."""
    # Very conservative: 12 weeks ago
    return timezone.now() - timedelta(weeks=12)


def _recent_time():
    """Make a timestamp that is definitely NOT inactive."""
    return timezone.now() - timedelta(seconds=10)


class TestTriggeredMails(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.user.date_last_login = timezone.now()
        self.user.save()

    def test_dont_trigger_no_login_mail_for_recent_login(self):
        self.user.date_last_login = _recent_time()
        self.user.save()

        with run_celery_tasks():
            main(dry_run=False)

        # No task should be created
        assert EmailTask.objects.filter(
            user=self.user, task_id__startswith=NO_LOGIN_PREFIX
        ).count() == 0

    def test_trigger_no_login_mail_enqueues_and_runs_success_path(self):
        """Inactive user -> EmailTask is enqueued and task runs without failing."""
        self.user.date_last_login = _inactive_time()
        self.user.save()

        # Intercept .emit so we don't depend on template rendering
        with capture_notifications(), run_celery_tasks():
            main(dry_run=False)

        tasks = EmailTask.objects.filter(
            user=self.user, task_id__startswith=NO_LOGIN_PREFIX
        ).order_by('id')
        assert tasks.count() == 1
        assert tasks.latest('id').status in {'SUCCESS'}

    @mock.patch('scripts.triggered_mails.send_no_login_email.delay')
    def test_trigger_no_login_mail_starts_EmailTask(self, mock_delay):
        """Inactive user -> EmailTask is enqueued and task runs without failing."""
        self.user.date_last_login = _inactive_time()
        self.user.save()

        with capture_notifications(expect_none=True):
            main(dry_run=False)

        tasks = EmailTask.objects.filter(
            user=self.user, task_id__startswith=NO_LOGIN_PREFIX
        ).order_by('id')
        assert tasks.count() == 1
        assert tasks.latest('id').status in {'PENDING'}

    def test_trigger_no_login_mail_failure_marks_task_failure(self):
        """If sending raises, the task should capture the exception and mark FAILURE."""
        self.user.date_last_login = _inactive_time()
        self.user.save()

        # Force the emit call to raise to exercise failure branch
        with mock.patch.object(
            NotificationType.Type.USER_NO_LOGIN.instance,
            'emit',
            side_effect=RuntimeError('kaboom'),
        ), run_celery_tasks():
            main(dry_run=False)

        task = EmailTask.objects.filter(
            user=self.user, task_id__startswith=NO_LOGIN_PREFIX
        ).latest('id')
        task.refresh_from_db()
        assert task.status == 'FAILURE'
        assert 'kaboom' in (task.error_message or '')

    def test_finder_returns_two_inactive_when_none_queued(self):
        """Two inactive users, no prior tasks -> finder returns both."""
        u1 = UserFactory(fullname='Jordan Mailata')
        u2 = UserFactory(fullname='Jake Elliot')
        u1.date_last_login = _inactive_time()
        u2.date_last_login = _inactive_time()
        u1.save()
        u2.save()

        users = list(find_inactive_users_without_enqueued_or_sent_no_login())
        ids = {u.id for u in users}
        assert ids == {u1.id, u2.id}

    def test_finder_excludes_users_with_existing_task(self):
        """Inactive users but one already has a no_login EmailTask -> excluded."""
        u1 = UserFactory(fullname='Jalen Hurts')
        u2 = UserFactory(fullname='Jason Kelece')
        u1.date_last_login = _inactive_time()
        u2.date_last_login = _inactive_time()
        u1.save()
        u2.save()

        # Pretend u2 already had this email flow (SUCCESS qualifies for exclusion)
        EmailTask.objects.create(
            task_id=f"{NO_LOGIN_PREFIX}existing-success",
            user=u2,
            status='SUCCESS',
        )

        users = list(find_inactive_users_without_enqueued_or_sent_no_login())
        ids = {u.id for u in users}
        assert ids == {u1.id}  # u2 excluded because of existing task
