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
        cls._yearmonth = YearMonth(2018, 2)  # February 2018
        cls._institution = InstitutionFactory()
        cls._now = datetime.datetime(2018, 2, 4, tzinfo=datetime.UTC)

        # Existing data for the primary institution
        cls._public_project = cls._create_affiliated_project(cls._institution, is_public=True, created=cls._now)
        cls._private_project = cls._create_affiliated_project(cls._institution, is_public=False, created=cls._now)
        cls._public_registration = cls._create_affiliated_registration(cls._institution, is_public=True, created=cls._now)
        cls._embargoed_registration = cls._create_affiliated_registration(cls._institution, is_public=False, created=cls._now)

        cls._published_preprint = cls._create_affiliated_preprint(cls._institution, is_public=True, created=cls._now)

        cls._logged_in_user = cls._create_logged_in_user(cls._institution, date_last_login=cls._now)
        cls._active_user = cls._create_active_user(cls._institution, date_confirmed=cls._now - datetime.timedelta(days=1))

    @classmethod
    def _create_affiliated_preprint(cls, institution, is_public, created):
        published_preprint = PreprintFactory(is_public=is_public)
        published_preprint.affiliated_institutions.add(institution)
        published_preprint.created = created
        published_preprint.save()
        return published_preprint

    @classmethod
    def _create_affiliated_project(cls, institution, is_public, created):
        project = ProjectFactory(is_public=is_public)
        project.affiliated_institutions.add(institution)
        project.created = created
        project.save()
        return project

    @classmethod
    def _create_affiliated_registration(cls, institution, is_public, created):
        registration = RegistrationFactory(is_public=is_public)
        registration.affiliated_institutions.add(institution)
        registration.created = created
        registration.save()
        return registration

    @classmethod
    def _create_logged_in_user(cls, institution, date_last_login):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        user.date_last_login = date_last_login
        user.save()
        return user

    @classmethod
    def _create_active_user(cls, institution, date_confirmed):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        user.date_confirmed = date_confirmed
        ProjectFactory(creator=user)  # adds log to make active
        log = user.logs.get()
        log.created = date_confirmed
        log.save()
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

    def test_report_generation_multiple_institutions(self):
        institution2 = InstitutionFactory()
        institution3 = InstitutionFactory()

        # Set up dates for different months
        now = datetime.datetime(2018, 2, 4, tzinfo=datetime.UTC)
        last_month = datetime.datetime(2018, 1, 15, tzinfo=datetime.UTC)
        next_month = datetime.datetime(2018, 3, 10, tzinfo=datetime.UTC)

        self._create_affiliated_project(institution2, is_public=True, created=now)
        self._create_affiliated_project(institution3, is_public=True, created=last_month)

        # Create future projects for self._institution (should not be counted)
        self._create_affiliated_project(self._institution, is_public=True, created=next_month)

        # Create users affiliated with different institutions
        self._create_active_user(institution2, date_confirmed=now)
        self._create_active_user(institution3, date_confirmed=last_month)

        # Run the reporter for the current month (February 2018)
        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        self.assertEqual(len(reports), 3)  # Reports for self._institution, institution2, institution3

        # Extract reports by institution
        report_institution = next(r for r in reports if r.institution_id == self._institution._id)
        report_institution2 = next(r for r in reports if r.institution_id == institution2._id)

        # Validate report for self._institution
        self.assertEqual(report_institution.public_project_count, 1)
        self.assertEqual(report_institution.private_project_count, 1)
        self.assertEqual(report_institution.user_count, 2)
        self.assertEqual(report_institution.monthly_active_user_count, 1)
        self.assertEqual(report_institution.monthly_logged_in_user_count, 1)

        # Validate report for institution2
        self.assertEqual(report_institution2.public_project_count, 1)
        self.assertEqual(report_institution2.private_project_count, 0)
        self.assertEqual(report_institution2.user_count, 1)
        self.assertEqual(report_institution2.monthly_active_user_count, 1)
        self.assertEqual(report_institution2.monthly_logged_in_user_count, 0)  # No logged-in users
