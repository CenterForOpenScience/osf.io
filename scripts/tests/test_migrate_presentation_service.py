from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory, UnconfirmedUserFactory
from framework.auth import Auth
from scripts.migrate_presentation_service import (
    do_migration, get_targets, migrate_project_contributed
)


class TestMigrateManualMergedUser(OsfTestCase):

    def test_get_targets(self):
        user1 = UserFactory.build(username='presentations@cos.io')
        user2 = UserFactory()
        user1.save()

        user_list = get_targets()
        assert user_list is not None
        assert len(user_list) is 1

        user3 = UserFactory.build(username='presentations@osf.io')
        user3.save()
        user_list = get_targets()
        assert len(user_list) is 2

    def test_migrate_project_contributed(self):
        user1 = UserFactory()

        fullname1 = 'hello world'
        email1 = 'test@example.com'
        project1 = ProjectFactory(creator=user1)
        user2 = project1.add_unregistered_contributor(
            fullname=fullname1, email=email1, auth=Auth(user=user1)
        )
        project1.save()
        assert project1.is_contributor(user2) is True
        assert len(project1.contributors) is 2

        migrate_project_contributed(user2)
        assert project1.is_contributor(user2) is False
        assert len(project1.contributors) is 1

        user3 = UserFactory()
        project2 = ProjectFactory(creator=user1)
        project2.add_contributor(user3)
        project2.save()

        assert project2.is_contributor(user3) is True
        assert len(project2.contributors) is 2

        migrate_project_contributed(user3)
        assert project2.is_contributor(user3) is False
        assert len(project2.contributors) is 1

    def test_do_migration(self):
        user1 = UserFactory()

        fullname1 = 'Presentation Service'
        email1 = 'presentations@cos.io'
        project1 = ProjectFactory(creator=user1)
        user2 = project1.add_unregistered_contributor(
            fullname=fullname1, email=email1, auth=Auth(user=user1)
        )
        project1.save()

        user3 = UserFactory.build(username='presentations@osf.io', fullname=fullname1)
        user3.save()
        project2 = ProjectFactory(creator=user1)
        project2.add_contributor(user3)
        project2.save()

        assert project1.is_contributor(user2) is True
        assert len(project1.contributors) is 2
        assert project2.is_contributor(user3) is True
        assert len(project2.contributors) is 2

        user_list = get_targets()
        do_migration(user_list)

        assert project2.is_contributor(user3) is False
        assert len(project2.contributors) is 1

        assert project1.is_contributor(user2) is False
        assert len(project1.contributors) is 1

        assert user2.is_disabled is True
        assert user3.is_disabled is True