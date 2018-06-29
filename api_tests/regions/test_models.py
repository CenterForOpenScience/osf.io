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
            region = RegionFactory()
            parent_node = ProjectFactory(creator=user, parent=parent_node)
            parent_node.get_addon('osfstorage').region = region

        # root project has three direct children
        for _ in range(0, 2):
            region = RegionFactory()
            parent_node = ProjectFactory(creator=user, parent=root_node)
            parent_node.get_addon('osfstorage').region = region

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

        # All registrations should have the same region as the node they are registered from.
        assert all(reg.registered_from.get_addon('osfstorage').region ==
            reg.get_addon('osfstorage').region for reg in regs)
