import mock
import pytest
from nose import tools as nt

from addons.osfstorage.models import Region
from addons.osfstorage.settings import DEFAULT_REGION_ID
from framework.auth import Auth
from addons.osfstorage.apps import OSFStorageAddonAppConfig
from osf.models import (
    RegistrationSchema,
    Registration,
    ExportData,
)
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegionFactory,
    DraftRegistrationFactory,
    ExportDataFactory,
)


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestRegion:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_with_different_regions(self, user):
        """
        A complex project configuration with many regions.
        :param user:
        :return:
        """
        parent_node = root_node = ProjectFactory(creator=user)

        # components have nested children
        for _ in range(0, 1):
            parent_node = ProjectFactory(creator=user, parent=parent_node)
            addon = parent_node.get_addon('osfstorage')
            addon.region = RegionFactory()
            addon.save()

        # root project has two direct children
        for _ in range(0, 1):
            parent_node = ProjectFactory(creator=user, parent=root_node)
            addon = parent_node.get_addon('osfstorage')
            addon.region = RegionFactory()
            addon.save()

        addon = root_node.get_addon('osfstorage')
        addon.region = RegionFactory()
        addon.save()

        return root_node

    @mock.patch('website.settings.ENABLE_ARCHIVER', False)
    def test_regions_stay_after_registration(self, user, project_with_different_regions):
        """
        Registering a project with components of different regions should keep those regions after registration.
        :param user:
        :param project_with_different_regions:
        :return:
        """
        schema = RegistrationSchema.objects.first()
        draft_reg = DraftRegistrationFactory(branched_from=project_with_different_regions)
        project_with_different_regions.register_node(schema, Auth(user=user), draft_reg)

        regs = Registration.objects.all()

        # Sanity check all regions are different from each other
        assert regs.count() == len({reg.get_addon('osfstorage').region._id for reg in regs})

        # All registrations should have the same region as the node they are registered from.
        assert all(reg.registered_from.get_addon('osfstorage').region ==
            reg.get_addon('osfstorage').region for reg in regs)

    def test_region_guid(self):
        region = RegionFactory()
        nt.assert_equal(region.guid, region._id)

    def test_provider_name(self):
        region = RegionFactory()
        nt.assert_not_equal(region.provider_name, 'osfstorage')
        nt.assert_equal(region.provider_name, 'glowcloud')

        region = RegionFactory(waterbutler_settings={
            'storage': {
                'provider': 'filesystem',
                'container': 'osf_storage',
                'use_public': True,
            }
        })
        nt.assert_equal(region.provider_name, 'osfstorage')

    def test_addon(self):
        region = RegionFactory()
        nt.assert_is_none(region.addon)

        region = RegionFactory(waterbutler_settings={
            'storage': {
                'provider': 'filesystem',
                'container': 'osf_storage',
                'use_public': True,
            }
        })
        nt.assert_true(isinstance(region.addon, OSFStorageAddonAppConfig))

    def test_provider_short_name(self):
        region = RegionFactory()
        nt.assert_is_none(region.provider_short_name)

        region = RegionFactory(waterbutler_settings={
            'storage': {
                'provider': 'filesystem',
                'container': 'osf_storage',
                'use_public': True,
            }
        })
        nt.assert_equal(region.provider_short_name, OSFStorageAddonAppConfig.short_name)

    def test_provider_full_name(self):
        region = RegionFactory()
        nt.assert_is_none(region.provider_full_name)

        region = RegionFactory(waterbutler_settings={
            'storage': {
                'provider': 'filesystem',
                'container': 'osf_storage',
                'use_public': True,
            }
        })
        nt.assert_equal(region.provider_full_name, OSFStorageAddonAppConfig.full_name)

    def test_has_export_data(self):
        region = RegionFactory(waterbutler_settings={'storage': {'provider': 'osfstorage'}})
        nt.assert_false(region.has_export_data)

        ExportDataFactory(source=region, status=ExportData.STATUS_ERROR)
        nt.assert_false(region.has_export_data)
        ExportDataFactory(source=region, status=ExportData.STATUS_RUNNING)
        nt.assert_false(region.has_export_data)
        ExportDataFactory(source=region, status=ExportData.STATUS_STOPPING)
        nt.assert_false(region.has_export_data)
        ExportDataFactory(source=region, status=ExportData.STATUS_STOPPED)
        nt.assert_false(region.has_export_data)

        ExportDataFactory(source=region, status=ExportData.STATUS_COMPLETED)
        nt.assert_true(region.has_export_data)
        ExportDataFactory(source=region, status=ExportData.STATUS_CHECKING)
        nt.assert_true(region.has_export_data)

    def test_location_ids_has_exported_data(self):
        region = RegionFactory(waterbutler_settings={'storage': {'provider': 'osfstorage'}})
        nt.assert_equal(len(region.location_ids_has_exported_data), 0)

        ExportDataFactory(source=region, status=ExportData.STATUS_ERROR)
        ExportDataFactory(source=region, status=ExportData.STATUS_RUNNING)
        ExportDataFactory(source=region, status=ExportData.STATUS_STOPPING)
        ExportDataFactory(source=region, status=ExportData.STATUS_STOPPED)

        export_data_1 = ExportDataFactory(source=region, status=ExportData.STATUS_COMPLETED)
        export_data_2 = ExportDataFactory(source=region, status=ExportData.STATUS_CHECKING)
        nt.assert_list_equal(list(region.location_ids_has_exported_data), [export_data_1.location.id, export_data_2.location.id])

    def test_has_same_settings_as_default_region_true(self):
        default_region = Region.objects.get(_id=DEFAULT_REGION_ID)
        region = RegionFactory(name=default_region.name,
                               waterbutler_credentials=default_region.waterbutler_credentials,
                               waterbutler_settings=default_region.waterbutler_settings)
        nt.assert_true(region.has_same_settings_as_default_region)

    def test_has_same_settings_as_default_region_false(self):
        region = RegionFactory()
        nt.assert_false(region.has_same_settings_as_default_region)
