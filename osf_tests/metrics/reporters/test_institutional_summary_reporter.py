import datetime
from django.test import TestCase
from osf.models import Preprint
from osf.metrics.reporters import InstitutionalSummaryMonthlyReporter
from osf.metrics.utils import YearMonth
from osf_tests.factories import (
    InstitutionFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory,
    UserFactory,
    NodeLicenseRecordFactory,
    RegionFactory,
    AuthUserFactory,
)
from addons.github.tests.factories import GitHubAccountFactory
from framework.auth import Auth


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

        if hasattr(Preprint, 'affiliated_institutions'):
            cls._published_preprint = PreprintFactory(creator=UserFactory(), is_public=True)
            cls._published_preprint.affiliated_institutions.add(cls._institution)

    @classmethod
    def _create_affiliated_project(cls, is_public):
        project = ProjectFactory(creator=UserFactory(), is_public=is_public)
        project.affiliated_institutions.add(cls._institution)
        return project

    @classmethod
    def _create_affiliated_registration(cls, is_public):
        registration = RegistrationFactory(creator=UserFactory(), is_public=is_public)
        registration.affiliated_institutions.add(cls._institution)
        return registration

    def configure_addon(self):

        addon_user = AuthUserFactory()
        auth_obj = Auth(user=addon_user)
        node = ProjectFactory(creator=addon_user)

        addon_user.add_addon('github')
        user_addon = addon_user.get_addon('github')
        oauth_settings = GitHubAccountFactory(display_name='john')
        oauth_settings.save()
        addon_user.external_accounts.add(oauth_settings)
        addon_user.save()

        node.add_addon('github', auth_obj)
        node_addon = node.get_addon('github')
        node_addon.user = 'john'
        node_addon.repo = 'youre-my-best-friend'
        node_addon.user_settings = user_addon
        node_addon.external_account = oauth_settings
        node_addon.save()

        user_addon.oauth_grants[node._id] = {oauth_settings._id: []}
        user_addon.save()

        return node

    def test_report_generation(self):
        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        self.assertEqual(len(reports), 1)

        report = reports[0]
        self.assertEqual(report.institution_id, self._institution._id)
        self.assertEqual(report.public_project_count, 1)
        self.assertEqual(report.private_project_count, 1)
        self.assertEqual(report.public_registration_count, 1)
        self.assertEqual(report.embargoed_registration_count, 1)
        self.assertEqual(report.published_preprint_count, 1 if hasattr(Preprint, 'affiliated_institutions') else 0)

    def test_license_counts(self):
        license_record = NodeLicenseRecordFactory()
        node_with_license = self._create_affiliated_project(is_public=True)
        node_with_license.node_license = license_record
        node_with_license.save()

        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        report = reports[0]

        self.assertIsNotNone(report.licenses)
        self.assertEqual(len(report.licenses), 2)

        default_license_count = next((l for l in report.licenses if l.name == 'Default (No license selected)'), None)
        self.assertEqual(default_license_count['total'], 4)

        license_count = next((l for l in report.licenses if l.name == license_record.name), None)
        self.assertEqual(license_count['total'], 1)

    def test_addons_count(self):
        github_addon_node = self.configure_addon()
        github_addon_node.affiliated_institutions.add(self._institution)

        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        report = reports[0]

        osfstorage_addon_count = next((l for l in report.addons if l.name == 'osfstorage'), None)
        self.assertTrue(osfstorage_addon_count['total'] == 7)

        github_addon_count = next((l for l in report.addons if l.name == 'github'), None)
        self.assertTrue(github_addon_count['total'] == 1)

    def test_storage_region_count(self):
        region = RegionFactory(_id='test1', name='Test Region #1')
        region2 = RegionFactory(_id='test2', name='Test Region #2')
        self._add_node_with_storage_region(region)
        self._add_node_with_storage_region(region2)
        self._add_node_with_storage_region(region2)

        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        report = reports[0]

        self.assertIsNotNone(report.storage_regions)
        self.assertEqual(len(report.storage_regions), 3)

        storage_region_count = next((l for l in report.storage_regions if l.name == 'Test Region #2'), None)
        self.assertEqual(storage_region_count['total'], 2)

    def _add_node_with_storage_region(self, region):
        project = self._create_affiliated_project(is_public=True)
        addon = project.get_addon('osfstorage')
        addon.region = region
        addon.save()
        self._institution.storage_regions.add(region)

    def test_department_count(self):
        user = self._public_project.creator
        user.add_or_update_affiliated_institution(self._institution, sso_department='Test Department #1')
        user = self._private_project.creator
        user.add_or_update_affiliated_institution(self._institution, sso_department='Test Department #2')

        reporter = InstitutionalSummaryMonthlyReporter()
        reports = list(reporter.report(self._yearmonth))
        report = reports[0]

        self.assertEqual(len(report.departments), 2)

        departments_count = next((l for l in report.departments if l.name == 'Test Department #1'), None)
        self.assertEqual(departments_count['total'], 1)
