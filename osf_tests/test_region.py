import pytest

from framework.auth import Auth

from osf.models import MetaSchema, Registration
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegionFactory
)

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

        # components nested five deep
        for _ in range(0, 5):
            parent_node = ProjectFactory(creator=user, parent=parent_node)
            addon = parent_node.get_addon('osfstorage')
            addon.region = RegionFactory()
            addon.save()

        # root project has three direct children
        for _ in range(0, 2):
            parent_node = ProjectFactory(creator=user, parent=root_node)
            addon = parent_node.get_addon('osfstorage')
            addon.region = RegionFactory()
            addon.save()

        addon = root_node.get_addon('osfstorage')
        addon.region = RegionFactory()
        addon.save()

        return root_node

    def test_regions_stay_after_registration(self, user, project_with_different_regions):
        """
        Registering a project with components of different regions should keep those regions after registration.
        :param user:
        :param project_with_different_regions:
        :return:
        """
        schema = MetaSchema.objects.first()
        project_with_different_regions.register_node(schema, Auth(user=user), '41-33')

        regs = Registration.objects.all()

        # Sanity check all regions are different from each other
        assert regs.count() == len({reg.get_addon('osfstorage').region._id for reg in regs})

        # All registrations should have the same region as the node they are registered from.
        assert all(reg.registered_from.get_addon('osfstorage').region ==
            reg.get_addon('osfstorage').region for reg in regs)
