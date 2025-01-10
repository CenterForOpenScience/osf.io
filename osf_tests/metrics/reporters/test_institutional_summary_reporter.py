import time
import datetime
import logging
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
from ._testutils import list_monthly_reports


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
        reporter = InstitutionalSummaryMonthlyReporter(self._yearmonth)
        reports = list_monthly_reports(reporter)
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
        last_month = datetime.datetime(2018, 1, 15, tzinfo=datetime.UTC)
        next_month = datetime.datetime(2018, 3, 10, tzinfo=datetime.UTC)

        self._create_affiliated_project(institution2, is_public=True, created=self._now)
        self._create_affiliated_project(institution3, is_public=True, created=last_month)

        # Create future projects for self._institution (should not be counted)
        self._create_affiliated_project(self._institution, is_public=True, created=next_month)

        # Create users affiliated with different institutions
        self._create_active_user(institution2, date_confirmed=self._now)
        self._create_active_user(institution3, date_confirmed=last_month)

        # Run the reporter for the current month (February 2018)
        reporter = InstitutionalSummaryMonthlyReporter(self._yearmonth)
        reports = list_monthly_reports(reporter)
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


class TestSummaryMonthlyReporterBenchmarker(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        cls._yearmonth = YearMonth(2018, 2)  # February 2018
        cls._institution = InstitutionFactory()
        cls._now = datetime.datetime(2018, 2, 4, tzinfo=datetime.UTC)
        cls.enable_benchmarking = True

    @classmethod
    def _create_affiliated_preprint(cls, institution, is_public, created, creator=None):
        published_preprint = PreprintFactory(is_public=is_public, creator=creator)
        published_preprint.affiliated_institutions.add(institution)
        published_preprint.created = created
        published_preprint.save()
        return published_preprint

    @classmethod
    def _create_affiliated_project(cls, institution, is_public, created, creator=None):
        project = ProjectFactory(is_public=is_public, creator=creator)
        project.affiliated_institutions.add(institution)
        project.created = created
        project.save()
        return project

    @classmethod
    def _create_affiliated_registration(cls, institution, is_public, created, creator=None):
        registration = RegistrationFactory(is_public=is_public, creator=creator)
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

    def test_high_counts_multiple_institutions(self):
        """
        Test the report generation with configurable high counts for institutions, users, and their objects.
        Benchmarking can be enabled by setting the 'enable_benchmarking' attribute to True.
        """
        # Check if benchmarking is enabled
        enable_benchmarking = self.enable_benchmarking

        # Configure counts (adjust these numbers as needed)
        additional_institution_count = 1  # Number of institutions (adjust as needed)
        users_per_institution = 3  # Number of users per institution (adjust as needed)
        objects_per_user = 3  # Number of objects per user (adjust as needed)

        # Timing variables
        if enable_benchmarking:
            total_start_time = time.time()
            data_creation_start_time = time.time()

        # Create institutions
        institutions = [self._institution]
        institutions += [InstitutionFactory() for _ in range(additional_institution_count)]

        if enable_benchmarking:
            institutions_creation_time = time.time()
            self.logger.info(
                f"Time taken to create {additional_institution_count + 1} institutions: {institutions_creation_time - data_creation_start_time:.2f} seconds")

        # Generate data for each institution
        if enable_benchmarking:
            users_creation_start_time = time.time()
        institution_users = {}
        for institution in institutions:
            # Create users for the institution
            users = []
            for _ in range(users_per_institution):
                user = AuthUserFactory()
                user.add_or_update_affiliated_institution(institution)
                user.date_last_login = self._now
                user.date_confirmed = self._now - datetime.timedelta(days=1)
                user.save()
                users.append(user)
            institution_users[institution] = users

        if enable_benchmarking:
            users_creation_time = time.time()
            self.logger.info(f"Time taken to create users: {users_creation_time - users_creation_start_time:.2f} seconds")

        # Create projects, registrations, and preprints for each user
        if enable_benchmarking:
            objects_creation_start_time = time.time()
        for institution in institutions:
            users = institution_users[institution]
            for user in users:
                for _ in range(objects_per_user):
                    self._create_affiliated_project(institution, is_public=True, created=self._now, creator=user)
                    self._create_affiliated_project(institution, is_public=False, created=self._now, creator=user)
                    self._create_affiliated_registration(institution, is_public=True, created=self._now, creator=user)
                    self._create_affiliated_registration(institution, is_public=False, created=self._now, creator=user)
                    self._create_affiliated_preprint(institution, is_public=True, created=self._now, creator=user)

        if enable_benchmarking:
            objects_creation_time = time.time()
            self.logger.info(
                f"Time taken to create objects: {objects_creation_time - objects_creation_start_time:.2f} seconds")
            data_creation_end_time = time.time()
            self.logger.info(
                f"Total time taken to create data: {data_creation_end_time - data_creation_start_time:.2f} seconds")

        # Run the reporter
        if enable_benchmarking:
            reporter_start_time = time.time()
        reporter = InstitutionalSummaryMonthlyReporter(self._yearmonth)
        reports = list_monthly_reports(reporter)
        assert len(reports) == additional_institution_count + 1

        if enable_benchmarking:
            reporter_end_time = time.time()
            self.logger.info(f"Time taken to run the reporter: {reporter_end_time - reporter_start_time:.2f} seconds")
            total_end_time = time.time()
            self.logger.info(f"Total test execution time: {total_end_time - total_start_time:.2f} seconds")

        self.assertEqual(len(reports), additional_institution_count + 1)

        # Validate counts for each institution
        expected_count = users_per_institution * objects_per_user
        for report in reports:
            self.assertEqual(report.public_project_count, expected_count)
            self.assertEqual(report.private_project_count, expected_count)
            self.assertEqual(report.public_registration_count, expected_count)
            self.assertEqual(report.embargoed_registration_count, expected_count)
            self.assertEqual(report.published_preprint_count, expected_count)
            self.assertEqual(report.user_count, users_per_institution)
            self.assertEqual(report.monthly_logged_in_user_count, users_per_institution)
