# -*- coding: utf-8 -*-
import mock
import pytest
import time

from collections import OrderedDict

from django.utils import timezone

from addons.osfstorage import settings as osfstorage_settings
from api_tests.utils import create_test_file
from framework.auth import Auth
from osf.management.commands.update_institution_project_counts import update_institution_project_counts
from osf.models import QuickFilesNode, RegistrationSchema
from osf.metrics import InstitutionProjectCounts, UserInstitutionProjectCounts
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    PreprintFactory,
    ProjectFactory,
    RegionFactory,
    UserFactory,
    DraftRegistrationFactory,
)
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
        super(TestDataStorageUsage, self).setUp()
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

    @pytest.fixture()
    def project(self, creator, is_public=True, is_deleted=False, region=None, parent=None):
        if region is None:
            region = self.region_us
        project = ProjectFactory(creator=creator, is_public=is_public, is_deleted=is_deleted)
        addon = project.get_addon('osfstorage')
        addon.region = region
        addon.save()

        return project

    @pytest.fixture()
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
    @pytest.mark.enable_quickfiles_creation
    def test_data_storage_usage_command(self):
        import logging
        logger = logging.getLogger(__name__)

        expected_summary_data = OrderedDict([
            ('date', None),
            ('total', 0),
            ('deleted', 0),
            ('registrations', 0),
            ('nd_quick_files', 0),
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
        region_ca = RegionFactory(_id='CA-1', name=u'Canada - Montréal')
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
        logger.debug(u'Public project, US: {}'.format(file_size))
        expected_summary_data['total'] += file_size
        expected_summary_data['nd_public_nodes'] += file_size
        expected_summary_data['united_states'] += file_size
        file_size = next(small_size)
        self.add_file_version(
            project_public_us_test_file,
            user=user,
            size=file_size,
        )
        logger.debug(u'Public project file version, US: {}'.format(file_size))
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
        logger.debug(u'Private project, AU: {}'.format(file_size))
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
        logger.debug('Before deletion: {}'.format(deleted_file.target.title))

        deleted_file.delete(user=user, save=True)
        logger.debug(u'Deleted project, DE: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['deleted'] += file_size
        expected_summary_data['germany_frankfurt'] += file_size
        logger.debug('After deletion: {}'.format(deleted_file.target.title))

        file_size = next(small_size)
        PreprintFactory(creator=user, file_size=file_size)  # preprint_us
        logger.debug(u'Preprint, US: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_preprints'] += file_size
        expected_summary_data['united_states'] += file_size

        user_addon.default_region_id = region_ca
        user_addon.save()
        file_size = next(small_size)
        preprint_with_supplement_ca = PreprintFactory(creator=user, file_size=file_size)
        logger.debug(u'Preprint, CA: {}'.format(file_size))

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
        logger.debug(u'Public supplemental project of Canadian preprint, US: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_supp_nodes'] += file_size
        expected_summary_data['nd_public_nodes'] += file_size
        expected_summary_data['australia_sydney'] += file_size

        file_size = next(small_size)
        withdrawn_preprint_us = PreprintFactory(creator=user, file_size=file_size)
        withdrawn_preprint_us.date_withdrawn = timezone.now()
        withdrawn_preprint_us.save()
        logger.debug(u'Withdrawn preprint, US: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_preprints'] += file_size
        expected_summary_data['united_states'] += file_size

        quickfiles_node_us = QuickFilesNode.objects.get(creator=user)
        file_size = next(small_size)
        create_test_file(target=quickfiles_node_us, user=user, size=file_size)
        logger.debug(u'Quickfile, US: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['nd_quick_files'] += file_size
        expected_summary_data['united_states'] += file_size

        file_size = next(small_size)
        quickfile_deleted = create_test_file(
            filename='deleted_test_file',
            target=quickfiles_node_us,
            user=user,
            size=file_size
        )
        quickfile_deleted.delete(user=user, save=True)
        logger.debug(u'Deleted quickfile, US: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['deleted'] += file_size
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
        logger.debug(u'Registration, US: {}'.format(file_size))

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
        logger.debug(u'Withdrawn registration, US: {}'.format(file_size))

        expected_summary_data['total'] += file_size
        expected_summary_data['united_states'] += file_size
        expected_summary_data['registrations'] += file_size

        actual_summary_data = process_usages(dry_run=True, page_size=2)

        actual_keys = actual_summary_data.keys()
        for key in actual_summary_data:
            logger.info('Actual field: {}'.format(key))
        expected_keys = expected_summary_data.keys()
        for key in expected_summary_data:
            logger.info('Expected field: {}'.format(key))
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
        institution.osfuser_set.add(user)
        institution.save()

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
        institution.osfuser_set.add(user)
        institution.save()

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
        institution.osfuser_set.add(user)
        institution.save()

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
