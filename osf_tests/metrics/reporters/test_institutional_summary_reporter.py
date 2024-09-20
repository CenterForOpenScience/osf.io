import datetime
from django.test import TestCase
from osf.metrics.reporters import InstitutionalSummaryMonthlyReporter
from osf.metrics.utils import YearMonth
from osf_tests.factories import (
    InstitutionFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory,
    AuthUserFactory,
)


class TestInstiSummaryMonthlyReporter(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls._yearmonth = YearMonth(2018, 2)
        cls._institution = InstitutionFactory()
        cls._now = datetime.datetime(2018, 2, 4, tzinfo=datetime.UTC)

        cls._public_project = cls._create_affiliated_project(is_public=True)
        cls._private_project = cls._create_affiliated_project(is_public=False)
        cls._public_registration = cls._create_affiliated_registration(is_public=True)
        cls._embargoed_registration = cls._create_affiliated_registration(is_public=False)

        cls._published_preprint = PreprintFactory(is_public=True)
        cls._published_preprint.affiliated_institutions.add(cls._institution)

        cls._logged_in_user = cls._create_logged_in_user()
        cls._active_user = cls._create_active_user()

    @classmethod
    def _create_affiliated_project(cls, is_public):
        project = ProjectFactory(is_public=is_public)
        project.affiliated_institutions.add(cls._institution)
        return project

    @classmethod
    def _create_affiliated_registration(cls, is_public):
        registration = RegistrationFactory(is_public=is_public)
        registration.affiliated_institutions.add(cls._institution)
        return registration

    @classmethod
    def _create_logged_in_user(cls):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(cls._institution)
        user.date_last_login = cls._now
        user.save()
        return user

    @classmethod
    def _create_active_user(cls):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(cls._institution)
        user.date_confirmed = cls._now - datetime.timedelta(days=1)
        user.save()
        return user

    def test_report_generation(self):
        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        self.assertEqual(len(reports), 1)

        report = reports[0]
        self.assertEqual(report.institution_id, self._institution._id)
        self.assertEqual(report.user_count, 2)  # _logged_in_user and _active_user
        self.assertEqual(report.public_project_count, 1)
        self.assertEqual(report.private_project_count, 1)
        self.assertEqual(report.public_registration_count, 1)
        self.assertEqual(report.embargoed_registration_count, 1)
        self.assertEqual(report.published_preprint_count, 1)
        self.assertEqual(report.storage_byte_count, 1337)  # test value for one file
        self.assertEqual(report.public_file_count, 1)
        self.assertEqual(report.monthly_logged_in_user_count, 1)
        self.assertEqual(report.monthly_active_user_count, 1)
