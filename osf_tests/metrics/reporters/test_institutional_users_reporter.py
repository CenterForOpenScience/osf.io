from __future__ import annotations
import dataclasses
import datetime
import unittest

from django.test import TestCase

from api_tests.utils import create_test_file
from osf import models as osfdb
from osf.metrics.reports import InstitutionalUserReport
from osf.metrics.reporters import InstitutionalUsersReporter
from osf.metrics.utils import YearMonth
from osf_tests.factories import (
    InstitutionFactory,
    PreprintFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
    EmbargoFactory,
)


def _patch_now(fakenow: datetime.datetime):
    return unittest.mock.patch('django.utils.timezone.now', return_value=fakenow)


class TestInstiUsersReporter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls._yearmonth = YearMonth(2012, 7)
        cls._now = datetime.datetime(
            cls._yearmonth.year,
            cls._yearmonth.month,
            13,  # just some day in the month
            tzinfo=datetime.UTC,
        )
        with _patch_now(cls._now):
            cls._institution = InstitutionFactory()
            cls._user_setup_with_nothing = _InstiUserSetup(0, 0, 0, 0, 0, cls._institution, cls._now)
            cls._user_setup_with_ones = _InstiUserSetup(1, 1, 1, 1, 1, cls._institution, cls._now)
            cls._user_setup_with_stuff = _InstiUserSetup(
                2, 3, 5, 3, 2, cls._institution, cls._now,
                orcid_id='1111-2222-3333-4444',
                department_name='blargl studies',
            )
            cls._user_setup_with_stuff.fill_uncounted_objects()

    def _assert_report_matches_setup(self, report: InstitutionalUserReport, setup: _InstiUserSetup):
        self.assertEqual(report.institution_id, setup.institution._id)
        # user info:
        self.assertEqual(report.user_id, setup.user._id)
        self.assertEqual(report.user_name, setup.user.fullname)
        self.assertEqual(report.department_name, setup.department_name)
        self.assertEqual(report.month_last_login, YearMonth.from_date(setup.user.date_last_login))
        if setup.month_last_active:
            self.assertEqual(report.month_last_active, YearMonth.from_date(setup.month_last_active))
        else:
            self.assertEqual(report.month_last_active, setup.month_last_active)

        self.assertEqual(report.account_creation_date, YearMonth.from_date(setup.user.created))
        self.assertEqual(report.orcid_id, setup.orcid_id)
        # counts (NOTE: report.public_file_count and report.storage_byte_count tested separately)
        self.assertEqual(report.public_project_count, setup.public_project_count)
        self.assertEqual(report.private_project_count, setup.private_project_count)
        self.assertEqual(report.public_registration_count, setup.public_registration_count)
        self.assertEqual(report.embargoed_registration_count, setup.embargoed_registration_count)
        self.assertEqual(report.published_preprint_count, setup.published_preprint_count)

    def test_no_users(self):
        _actual_reports = list(InstitutionalUsersReporter().report(self._yearmonth))
        self.assertEqual(_actual_reports, [])

    def test_one_user_with_nothing(self):
        self._user_setup_with_nothing.affiliate_user()
        _reports = list(InstitutionalUsersReporter().report(self._yearmonth))
        self.assertEqual(len(_reports), 1)
        self._assert_report_matches_setup(_reports[0], self._user_setup_with_nothing)

    def test_one_user_with_ones(self):
        self._user_setup_with_ones.affiliate_user()
        _reports = list(InstitutionalUsersReporter().report(self._yearmonth))
        self.assertEqual(len(_reports), 1)
        self._assert_report_matches_setup(_reports[0], self._user_setup_with_ones)

    def test_one_user_with_stuff_and_no_files(self):
        self._user_setup_with_stuff.affiliate_user()
        _reports = list(InstitutionalUsersReporter().report(self._yearmonth))
        self.assertEqual(len(_reports), 1)
        self._assert_report_matches_setup(_reports[0], self._user_setup_with_stuff)
        self.assertEqual(_reports[0].public_file_count, 2)  # preprint 2 files
        self.assertEqual(_reports[0].storage_byte_count, 2674)  # preprint bytes

    def test_one_user_with_stuff_and_a_file(self):
        self._user_setup_with_stuff.affiliate_user()
        _user = self._user_setup_with_stuff.user
        _project = _user.nodes.first()
        with _patch_now(self._now):
            create_test_file(target=_project, user=_user, size=37)
        (_report,) = InstitutionalUsersReporter().report(self._yearmonth)
        self._assert_report_matches_setup(_report, self._user_setup_with_stuff)
        self.assertEqual(_report.public_file_count, 3)  # 2 preprint files
        self.assertEqual(_report.storage_byte_count, 2711)  # 2 preprint files

    def test_one_user_with_stuff_and_multiple_files(self):
        self._user_setup_with_stuff.affiliate_user()
        _user = self._user_setup_with_stuff.user
        _project = _user.nodes.first()
        with _patch_now(self._now):
            create_test_file(target=_project, user=_user, size=37, filename='b')
            create_test_file(target=_project, user=_user, size=73, filename='bl')
            _component = ProjectFactory(parent=_project, creator=_user, is_public=True)
            _component.affiliated_institutions.add(self._institution)
            create_test_file(target=_component, user=_user, size=53, filename='bla')
            create_test_file(target=_component, user=_user, size=51, filename='blar')
            create_test_file(target=_component, user=_user, size=47, filename='blarg')
        (_report,) = InstitutionalUsersReporter().report(self._yearmonth)
        self._assert_report_matches_setup(_report, self._user_setup_with_stuff)
        self.assertEqual(_report.public_file_count, 7)  # 2 preprint files
        self.assertEqual(_report.storage_byte_count, 2935)  # 2 preprint files + 37 + 73 + 53 + 51 + 47

    def test_several_users(self):
        _setups = [
            self._user_setup_with_nothing,
            self._user_setup_with_ones,
            self._user_setup_with_stuff,
        ]
        for _setup in _setups:
            _setup.affiliate_user()
        _setup_by_userid = {
            _setup.user._id: _setup
            for _setup in _setups
        }
        _reports = list(InstitutionalUsersReporter().report(self._yearmonth))
        self.assertEqual(len(_reports), len(_setup_by_userid))
        for _actual_report in _reports:
            _setup = _setup_by_userid[_actual_report.user_id]
            self._assert_report_matches_setup(_actual_report, _setup)


@dataclasses.dataclass
class _InstiUserSetup:
    '''helper class to simplify database setup for a test-case

    (note: public_file_count and storage_byte_count set up separately)
    '''
    public_project_count: int
    private_project_count: int
    public_registration_count: int
    embargoed_registration_count: int
    published_preprint_count: int
    institution: osfdb.Institution
    now: datetime.datetime
    department_name: str | None = None
    orcid_id: str | None = None
    user: osfdb.OSFUser = dataclasses.field(init=False)
    month_last_active: YearMonth | None = dataclasses.field(init=False)

    def __post_init__(self):
        self.user = UserFactory(
            date_last_login=self.now,
            external_identity=(
                {'ORCID': {self.orcid_id: 'VERIFIED'}}
                if self.orcid_id
                else {}
            ),
        )
        self._add_affiliations(self._generate_counted_objects())
        node_logs = self.user.logs.order_by('-created')
        preprint_logs = self.user.preprint_logs.order_by('-created')

        dates = filter(bool, [
            node_logs.values_list('created', flat=True).first(),
            preprint_logs.values_list('created', flat=True).first(),
        ])

        self.month_last_active = max(dates, default=None)

    def affiliate_user(self):
        self.user.add_or_update_affiliated_institution(
            self.institution,
            sso_department=self.department_name,
        )

    @property
    def future_timestamp(self):
        return self.now + datetime.timedelta(days=123)

    def fill_uncounted_objects(self):
        # uncounted because not affiliated:
        self._add_public_project()
        self._add_private_project()
        self._add_public_registration()
        self._add_embargoed_registration()
        self._add_published_preprint()
        # uncounted because affiliated with another institution:
        self._add_affiliations((
            self._add_public_project(),
            self._add_private_project(),
            self._add_public_registration(),
            self._add_embargoed_registration(),
            self._add_published_preprint(),
        ), institution=InstitutionFactory())
        # uncounted because created after the report's time range:
        with _patch_now(self.future_timestamp):
            self._add_affiliations((
                self._add_public_project(),
                self._add_private_project(),
                self._add_public_registration(),
                self._add_embargoed_registration(),
                self._add_published_preprint(),
            ))

    def _add_affiliations(self, objs, institution=None):
        for _obj in objs:
            if _obj is not None:
                _obj.affiliated_institutions.add(institution or self.institution)

    def _generate_counted_objects(self):
        for _ in range(self.public_project_count):
            yield self._add_public_project()
        for _ in range(self.private_project_count):
            yield self._add_private_project()
        for _ in range(self.public_registration_count):
            yield self._add_public_registration()
        for _ in range(self.embargoed_registration_count):
            yield self._add_embargoed_registration()
        for _ in range(self.published_preprint_count):
            yield self._add_published_preprint()

    def _add_public_project(self) -> osfdb.Node:
        return ProjectFactory(
            creator=self.user,
            is_public=True,
        )

    def _add_private_project(self) -> osfdb.Node:
        return ProjectFactory(
            creator=self.user,
            is_public=False,
        )

    def _add_public_registration(self) -> osfdb.Registration:
        return RegistrationFactory(
            creator=self.user,
            is_public=True,
        )

    def _add_embargoed_registration(self) -> osfdb.Registration:
        return RegistrationFactory(
            creator=self.user,
            is_public=False,
            embargo=EmbargoFactory(
                user=self.user,
                end_date=self.future_timestamp,
            ),
        )

    def _add_published_preprint(self) -> osfdb.Preprint | None:
        return PreprintFactory(
            creator=self.user,
            is_public=True,
        )
