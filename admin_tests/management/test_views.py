import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from admin.management import views
from osf.models import StuckRegistrationReportConfig
from osf.models.stuck_registration_report import StuckRegistrationReportCadence
from osf_tests.factories import AuthUserFactory

pytestmark = pytest.mark.django_db

Cadence = StuckRegistrationReportCadence


def post(view, data):
    request = RequestFactory().post('/fake_path', data)
    request.user = AuthUserFactory()
    setattr(request, 'session', 'session')
    setattr(request, '_messages', FallbackStorage(request))
    response = view.as_view()(request)
    assert response.status_code == 302
    return [str(message) for message in request._messages]


@pytest.mark.urls('admin.base.urls')
class TestStuckRegistrationReport:

    def test_saves_recipients_and_cadence(self):
        post(views.StuckRegistrationReport, {
            'report_emails': 'support@osf.io, product@osf.io',
            'report_cadence': Cadence.DAILY,
        })
        config = StuckRegistrationReportConfig.load()
        assert config.emails == ['support@osf.io', 'product@osf.io']
        assert config.cadence == Cadence.DAILY

    def test_updates_the_settings_already_saved(self):
        StuckRegistrationReportConfig.objects.create(emails=['support@osf.io'], cadence=Cadence.DAILY)
        post(views.StuckRegistrationReport, {
            'report_emails': '',
            'report_cadence': Cadence.WEEKLY,
        })
        assert StuckRegistrationReportConfig.objects.count() == 1
        config = StuckRegistrationReportConfig.load()
        assert config.emails == []
        assert config.cadence == Cadence.WEEKLY

    @pytest.mark.parametrize('emails', [
        'a@osf.io, b@osf.io, c@osf.io, d@osf.io',
        'support@osf.io, product',
    ])
    def test_keeps_the_saved_settings_when_the_addresses_are_not_good(self, emails):
        StuckRegistrationReportConfig.objects.create(emails=['support@osf.io'], cadence=Cadence.DAILY)
        messages = post(views.StuckRegistrationReport, {
            'report_emails': emails,
            'report_cadence': Cadence.WEEKLY,
        })
        assert 'try again' in messages[0]
        config = StuckRegistrationReportConfig.load()
        assert config.emails == ['support@osf.io']
        assert config.cadence == Cadence.DAILY

    def test_keeps_the_saved_settings_when_the_cadence_is_not_good(self):
        StuckRegistrationReportConfig.objects.create(emails=['support@osf.io'], cadence=Cadence.DAILY)
        messages = post(views.StuckRegistrationReport, {
            'report_emails': 'support@osf.io',
            'report_cadence': 'hourly',
        })
        assert 'try again' in messages[0]
        assert StuckRegistrationReportConfig.load().cadence == Cadence.DAILY
