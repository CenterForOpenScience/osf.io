from unittest import mock
import pytest
import time

from collections import OrderedDict

from django.utils import timezone

from addons.osfstorage import settings as osfstorage_settings
from api_tests.utils import create_test_file
from framework.auth import Auth
from osf.management.commands.update_institution_project_counts import update_institution_project_counts
from osf.management.commands.project_to_draft_registration_contributor_sync import retrieve_draft_registrations_to_sync, project_to_draft_registration_contributor_sync
from osf.models import RegistrationSchema
from osf.metrics import InstitutionProjectCounts, UserInstitutionProjectCounts
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    PreprintFactory,
    ProjectFactory,
    RegistrationFactory,
    RegionFactory,
    UserFactory,
    DraftRegistrationFactory,
)
from osf.utils.permissions import ADMIN, WRITE, READ
from tests.base import DbTestCase
from osf.management.commands.data_storage_usage import (
    process_usages,
)


# Using powers of two so that any combination of file sizes will give a unique total
# If a summary value is incorrect, subtract out the values that are correct and convert
# to binary. Each of the 1s will correspond something that wasn't handled properly.
def next_file_size():
    size = 1
    while True:
        yield size
        size *= 2


class TestDataStorageUsage(DbTestCase):

    def setUp(self):
        super().setUp()
        self.region_us = RegionFactory(_id='US', name='United States')

    @staticmethod
    def add_file_version(file_to_version, user, size, version=1):
        file_to_version.create_version(user, {
            'object': '06d80e' + str(version),
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': size,
            'contentType': 'img/png'
        }).save()

    def project(self, creator, is_public=True, is_deleted=False, region=None, parent=None):
        if region is None:
            region = self.region_us
        project = ProjectFactory(creator=creator, is_public=is_public, is_deleted=is_deleted)
        addon = project.get_addon('osfstorage')
        addon.region = region
        addon.save()

        return project

    def registration(self, project, creator, withdrawn=False):
        schema = RegistrationSchema.objects.first()
        draft_reg = DraftRegistrationFactory(branched_from=project)
        registration = project.register_node(schema, Auth(user=creator), draft_reg)
        registration.is_public = True
        registration.save()

        if withdrawn:
            registration.retract_registration(creator)
            withdrawal = registration.retraction
            token = list(withdrawal.approval_state.values())[0]['approval_token']
            with mock.patch('osf.models.AbstractNode.update_search'):
                withdrawal.approve_retraction(creator, token)
            withdrawal.save()

        return registration

    @pytest.fixture()
    def component(self, parent, user):
        return ProjectFactory(creator=user, parent=parent)

    @pytest.fixture()
    def project_deleted(self, user):
        return ProjectFactory(creator=user, is_deleted=True)

    @mock.patch('website.settings.ENABLE_ARCHIVER', False)
    def test_data_storage_usage_command(self):
        import logging
        logger = logging.getLogger(__name__)

        expected_summary_data = OrderedDict([
            ('date', None),
            ('total', 0),
            ('deleted', 0),
            ('registrations', 0),
            ('nd_public_nodes', 0),
            ('nd_private_nodes', 0),
            ('nd_preprints', 0),
            ('nd_supp_nodes', 0),
            ('canada_montreal', 0),
            ('australia_sydney', 0),
            ('germany_frankfurt', 0),
            ('united_states', 0),
        ])
        user = UserFactory()
        user_addon = user.get_addon('osfstorage')
        user_addon.default_region_id = self.region_us
        region_ca = RegionFactory(_id='CA-1', name='Canada - Montréal')
        region_de = RegionFactory(_id='DE-1', name='Germany - Frankfurt')
        region_au = RegionFactory(_id='AU-1', name='Australia - Sydney')

        project_public_us = self.project(creator=user, is_public=True)
        small_size = next_file_size()
        file_size = next(small_size)
        project_public_us_test_file = create_test_file(
            target=project_public_us,
            user=user,
            size=file_size
        )
        logger.debug(f'Public project, US: {file_size}')
        expected_summary_data['total'] += file_size
        expected_summary_data['nd_public_nodes'] += file_size
        expected_summary_data['united_states'] += file_size
        file_size = next(small_size)
        self.add_file_version(
            project_public_us_test_file,
            user=user,
            size=file_size,
        )
        logger.debug(f'Public project file version, US: {file_size}')
        expected_summary_data['total'] += file_size
        expected_summary_data['nd_public_nodes'] += file_size
        expected_summary_data['united_states'] += file_size

        project_private_au = self.project(creator=user, is_public=False, region=region_au)
        file_size = next(small_size)
        create_test_file(
            target=project_private_au,
            user=user,
            size=file_size
        )
        logger.debug(f'Private project, AU: {file_size}')
        expected_summary_data['total'] += file_size
        expected_summary_data['nd_private_nodes'] += file_size
        expected_summary_data['australia_sydney'] += file_size

        component_private_small_deleted_de = self.project(
            creator=user,
            is_public=False,
            region=region_de,
            parent=project_public_us
        )
        file_size = next(small_size)
        deleted_file = create_test_file(
            target=component_private_small_deleted_de,
            user=user,
            size=file_size,
        )
        logger.debug(f'Before deletion: {deleted_file.target.title}')

        deleted_file.delete(user=user, save=True)
        logger.debug(f'Deleted project, DE: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['deleted'] += file_size
        expected_summary_data['germany_frankfurt'] += file_size
        logger.debug(f'After deletion: {deleted_file.target.title}')

        file_size = next(small_size)
        PreprintFactory(creator=user, file_size=file_size)  # preprint_us
        logger.debug(f'Preprint, US: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_preprints'] += file_size
        expected_summary_data['united_states'] += file_size

        user_addon.default_region_id = region_ca
        user_addon.save()
        file_size = next(small_size)
        preprint_with_supplement_ca = PreprintFactory(creator=user, file_size=file_size)
        logger.debug(f'Preprint, CA: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_preprints'] += file_size
        expected_summary_data['canada_montreal'] += file_size
        user_addon.default_region_id = self.region_us
        user_addon.save()
        supplementary_node_public_au = self.project(creator=user, is_public=True, region=region_au)
        preprint_with_supplement_ca.node = supplementary_node_public_au
        preprint_with_supplement_ca.save()
        file_size = next(small_size)
        create_test_file(
            target=supplementary_node_public_au,
            user=user,
            size=file_size
        )
        logger.debug(f'Public supplemental project of Canadian preprint, US: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_supp_nodes'] += file_size
        expected_summary_data['nd_public_nodes'] += file_size
        expected_summary_data['australia_sydney'] += file_size

        file_size = next(small_size)
        withdrawn_preprint_us = PreprintFactory(creator=user, file_size=file_size)
        withdrawn_preprint_us.date_withdrawn = timezone.now()
        withdrawn_preprint_us.save()
        logger.debug(f'Withdrawn preprint, US: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_preprints'] += file_size
        expected_summary_data['united_states'] += file_size

        project_to_register_us = self.project(creator=user, is_public=True, region=self.region_us)

        registration = self.registration(project=project_to_register_us, creator=user)
        file_size = next(small_size)
        create_test_file(
            target=registration,
            user=user,
            size=file_size
        )
        assert registration.get_addon('osfstorage').region == self.region_us
        logger.debug(f'Registration, US: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['united_states'] += file_size
        expected_summary_data['registrations'] += file_size

        withdrawal = self.registration(project=project_to_register_us, creator=user, withdrawn=True)
        file_size = next(small_size)
        create_test_file(
            target=withdrawal,
            user=user,
            size=file_size
        )
        logger.debug(f'Withdrawn registration, US: {file_size}')

        expected_summary_data['total'] += file_size
        expected_summary_data['united_states'] += file_size
        expected_summary_data['registrations'] += file_size

        actual_summary_data = process_usages(dry_run=True, page_size=2)

        actual_keys = actual_summary_data.keys()
        for key in actual_summary_data:
            logger.info(f'Actual field: {key}')
        expected_keys = expected_summary_data.keys()
        for key in expected_summary_data:
            logger.info(f'Expected field: {key}')
        assert actual_keys == expected_keys
        assert len(actual_keys) != 0

        for key in actual_keys:
            if key != 'date':
                assert (key, expected_summary_data[key]) == (key, actual_summary_data[key])


@pytest.mark.es
@pytest.mark.django_db
class TestInstitutionMetricsUpdate:

    @pytest.fixture()
    def institution(self):
        # Private: 14, Public: 4
        return InstitutionFactory()

    @pytest.fixture()
    def user1(self, institution):
        # Private: 4, Public: 4 (+1 from user2 fixture)
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)

        for i in range(5):
            project = ProjectFactory(creator=user, is_public=False)
            project.affiliated_institutions.add(institution)
            project.save()

        project.delete()

        for i in range(3):
            project = ProjectFactory(creator=user, is_public=True)
            project.affiliated_institutions.add(institution)
            project.save()

        ProjectFactory(creator=user, is_public=True)
        ProjectFactory(creator=user, is_public=False)

        return user

    @pytest.fixture()
    def user2(self, institution, user1):
        # Private: 10, Public: 1
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)

        for i in range(10):
            project = ProjectFactory(creator=user, is_public=False)
            project.affiliated_institutions.add(institution)
            project.save()
        for i in range(1):
            project = ProjectFactory(creator=user, is_public=True)
            project.add_contributor(user1)
            project.affiliated_institutions.add(institution)
            project.save()

        return user

    @pytest.fixture()
    def user3(self, institution):
        # Private: 0, Public: 0
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)

        return user

    @pytest.fixture()
    def user4(self):
        # Projects should not be included in results
        user = AuthUserFactory()

        for i in range(3):
            project = ProjectFactory(creator=user, is_public=False)
            project.save()
        for i in range(6):
            project = ProjectFactory(creator=user, is_public=True)
            project.save()

        return user

    def test_update_institution_counts(self, app, institution, user1, user2, user3, user4):
        update_institution_project_counts()

        time.sleep(2)

        user_search = UserInstitutionProjectCounts.get_current_user_metrics(institution)
        user_results = user_search.execute()
        sorted_results = sorted(user_results, key=lambda x: x['private_project_count'])

        user3_record = sorted_results[0]
        user1_record = sorted_results[1]
        user2_record = sorted_results[2]

        assert user1_record['user_id'] == user1._id
        assert user1_record['public_project_count'] == 4
        assert user1_record['private_project_count'] == 4

        assert user2_record['user_id'] == user2._id
        assert user2_record['public_project_count'] == 1
        assert user2_record['private_project_count'] == 10

        assert user3_record['user_id'] == user3._id
        assert user3_record['public_project_count'] == 0
        assert user3_record['private_project_count'] == 0

        institution_results = InstitutionProjectCounts.get_latest_institution_project_document(institution)

        assert institution_results['public_project_count'] == 4
        assert institution_results['private_project_count'] == 14


@pytest.mark.django_db
class TestProjectDraftRegContributorSync:
    @pytest.fixture()
    def initiator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def draft_reg_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_admin_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_read_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, initiator):
        project = ProjectFactory(creator=initiator)
        return project

    @pytest.fixture()
    def active_draft_registration(self, project, initiator):
        return DraftRegistrationFactory(branched_from=project, initiator=initiator)

    @pytest.fixture()
    def inactive_draft_registration(self, project, initiator):
        draft_reg = DraftRegistrationFactory(branched_from=project, initiator=initiator)
        RegistrationFactory(draft_registration=draft_reg, creator=initiator)
        return draft_reg

    @pytest.fixture()
    def active_draft_registration_multiple_contributor(self, project, initiator, draft_reg_contributor):
        draft_reg = DraftRegistrationFactory(branched_from=project, initiator=initiator)
        draft_reg.add_contributor(draft_reg_contributor, WRITE)
        return draft_reg

    @pytest.fixture()
    def no_project_draft_registration(self, initiator):
        return DraftRegistrationFactory()

    def test_draft_reg_to_sync_retrieval(
            self, app, active_draft_registration, inactive_draft_registration, active_draft_registration_multiple_contributor, no_project_draft_registration):
        # Tests if the function used to retrieve draft registrations to copy project contributors
        # to is limited to those without registrations
        active_unsynced_draft_regs = retrieve_draft_registrations_to_sync()
        assert active_draft_registration in active_unsynced_draft_regs
        assert inactive_draft_registration not in active_unsynced_draft_regs
        assert no_project_draft_registration not in active_unsynced_draft_regs
        assert active_draft_registration_multiple_contributor not in active_unsynced_draft_regs

    def test_project_draft_reg_contributor_sync(
            self, app, initiator, project_admin_contributor,
            project_read_contributor, project, active_draft_registration):
        # Contributors added to the project here because the draft registration should be created with a single contributor (the initiator)
        project.add_contributor(project_admin_contributor, ADMIN)
        project.add_contributor(project_read_contributor, READ)
        # The removal of the initiator from the project ensures that contributors are copied from the
        # project but without overwriting the draft registration contributor permission
        project.remove_contributor(initiator, auth=project_admin_contributor.auth, log=False)
        assert project_admin_contributor in project.contributors.all()
        assert project_read_contributor in project.contributors.all()
        assert initiator not in project.contributors.all()

        assert active_draft_registration.contributors.count() == 1
        assert initiator in active_draft_registration.contributors.all()
        assert project_admin_contributor not in active_draft_registration.contributors.all()
        assert project_read_contributor not in active_draft_registration.contributors.all()

        project_to_draft_registration_contributor_sync()

        assert initiator in active_draft_registration.contributors.all()
        assert project_admin_contributor in active_draft_registration.contributors.all()
        assert project_read_contributor in active_draft_registration.contributors.all()
        assert active_draft_registration.contributors.count() == 3

        assert active_draft_registration.has_permission(initiator, ADMIN)
        assert active_draft_registration.has_permission(project_admin_contributor, ADMIN)
        assert active_draft_registration.has_permission(project_read_contributor, READ)
