import pytest
from unittest import mock

from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from osf.management.commands.populate_notification_types import populate_notification_types
from osf.management.commands.restart_stuck_registrations import restart_stuck_registrations
from osf.models import NodeLog, StuckRegistrationReportConfig
from osf.models.stuck_registration_report import StuckRegistrationReportCadence
from osf_tests.factories import RegistrationFactory
from tests.utils import capture_notifications
from website.archiver import ARCHIVER_INITIATED
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA

Cadence = StuckRegistrationReportCadence


def reported_registrations(notifications):
    return notifications['emits'][0]['kwargs']['event_context']['registrations']


def change_source_node_after_registration(registration):
    NodeLog.objects.create(
        node=registration.registered_from,
        action='addon_removed',
        user=registration.creator,
        date=timezone.now(),
    )


@pytest.mark.django_db
class TestStuckRegistrationReportConfig:

    def test_load_returns_the_one_row(self):
        config = StuckRegistrationReportConfig.load()
        assert config.cadence == Cadence.DAILY
        assert StuckRegistrationReportConfig.load() == config
        StuckRegistrationReportConfig(emails=['support@osf.io']).save()
        assert StuckRegistrationReportConfig.objects.count() == 1

    def test_parse_recipients(self):
        assert StuckRegistrationReportConfig.parse_recipients('') == []
        assert StuckRegistrationReportConfig.parse_recipients(
            'support@osf.io, product@osf.io;eng@osf.io'
        ) == ['support@osf.io', 'product@osf.io', 'eng@osf.io']
        with pytest.raises(ValidationError):
            StuckRegistrationReportConfig.parse_recipients('a@osf.io, b@osf.io, c@osf.io, d@osf.io')
        with pytest.raises(ValidationError):
            StuckRegistrationReportConfig.parse_recipients('support@osf.io, product')

    def test_report_is_due(self):
        config = StuckRegistrationReportConfig(emails=['support@osf.io'], cadence=Cadence.DAILY)
        assert config.report_is_due()
        config.last_sent = timezone.now()
        assert not config.report_is_due()
        assert config.report_is_due(now=timezone.now() + timedelta(days=1))
        assert not StuckRegistrationReportConfig(cadence=Cadence.INSTANT).report_is_due()


@pytest.mark.django_db
class TestRestartStuckRegistrations:

    @pytest.fixture(autouse=True)
    def notification_type(self):
        populate_notification_types(restore_one='desk_archive_restart_report')

    @pytest.fixture()
    def restart(self):
        with mock.patch('osf.management.commands.force_archive.archive') as archive, \
                mock.patch('scripts.check_manual_restart_approval.delayed_manual_restart_approval') as approval:
            yield archive, approval

    @pytest.fixture()
    def stuck_registration(self):
        registration = RegistrationFactory()
        archive_job = registration.archive_job
        archive_job._set_target('osfstorage')
        archive_job.datetime_initiated = timezone.now() - ARCHIVE_TIMEOUT_TIMEDELTA - timedelta(hours=1)
        archive_job.status = ARCHIVER_INITIATED
        archive_job.sent = False
        archive_job.done = False
        archive_job.save()
        return registration

    @pytest.fixture()
    def config(self):
        return StuckRegistrationReportConfig.objects.create(
            emails=['support@osf.io'],
            cadence=Cadence.INSTANT,
        )

    def test_stuck_registration_is_restarted(self, stuck_registration, restart):
        archive, approval = restart
        restarted, need_a_person = restart_stuck_registrations()
        assert restarted == 1
        assert need_a_person == 0
        assert archive.call_args[0][0] == stuck_registration
        approval.delay.assert_called_once_with(stuck_registration._id, delay_minutes=5)

    def test_registration_is_left_alone_when_its_source_node_changed(self, stuck_registration, restart, config):
        archive, _ = restart
        change_source_node_after_registration(stuck_registration)
        with capture_notifications() as notifications:
            restarted, need_a_person = restart_stuck_registrations()
        archive.assert_not_called()
        assert restarted == 0
        assert need_a_person == 1
        assert reported_registrations(notifications) == [{
            'registration__id': stuck_registration._id,
            'url': stuck_registration.absolute_url,
            'result': 'needs manual intervention',
        }]

    def test_report_goes_to_every_configured_address(self, stuck_registration, restart, config):
        config.emails = ['support@osf.io', 'product@osf.io']
        config.save()
        with capture_notifications() as notifications:
            restart_stuck_registrations()
        addresses = [emit['kwargs']['destination_address'] for emit in notifications['emits']]
        assert addresses == config.emails
        assert reported_registrations(notifications)[0]['result'] == 'restarted'
        config.refresh_from_db()
        assert config.last_sent

    def test_report_waits_for_the_configured_cadence(self, stuck_registration, restart, config):
        archive, _ = restart
        config.cadence = Cadence.WEEKLY
        config.last_sent = timezone.now() - timedelta(days=1)
        config.save()
        with capture_notifications(expect_none=True):
            restart_stuck_registrations()
        archive.assert_called_once()

    def test_no_report_when_no_address_is_configured(self, stuck_registration, restart):
        with capture_notifications(expect_none=True):
            restart_stuck_registrations()
        assert StuckRegistrationReportConfig.load().last_sent is None

    def test_no_report_when_nothing_is_stuck(self, restart, config):
        with capture_notifications(expect_none=True):
            restarted, need_a_person = restart_stuck_registrations()
        assert restarted == 0
        assert need_a_person == 0
        config.refresh_from_db()
        assert config.last_sent is None

    def test_registration_deleted_since_the_audit_is_skipped(self, stuck_registration, restart):
        archive, _ = restart
        with mock.patch('osf.models.Registration.load', return_value=None):
            restarted, need_a_person = restart_stuck_registrations()
        assert restarted == 0
        assert need_a_person == 0
        archive.assert_not_called()

    def test_dry_run_neither_restarts_nor_sends_emails(self, stuck_registration, restart, config):
        archive, approval = restart
        with capture_notifications(expect_none=True):
            restarted, _ = restart_stuck_registrations(dry_run=True)
        assert restarted == 1
        archive.assert_not_called()
        approval.delay.assert_not_called()
        config.refresh_from_db()
        assert config.last_sent is None
