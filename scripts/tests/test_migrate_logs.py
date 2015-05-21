from website.models import Node
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, NodeFactory
from scripts.migrate_logs import (
    do_migration, get_targets
)


class TestMigrateLogs(OsfTestCase):

    def tearDown(self):
        OsfTestCase.tearDown(self)
        Node.remove()

    def test_get_targets(self):
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        project1.save()
        project2.save()

        node_list1 = get_targets()
        assert node_list1 is not None
        assert len(node_list1) is 2

        project1.is_deleted = True
        project1.save()

        node_list2 = get_targets()
        assert node_list2 is not None
        assert len(node_list2) is 1

    def test_do_migration(self):
        project = ProjectFactory()
        user = UserFactory()
        node = NodeFactory(parent=project)
        node.add_contributor(contributor=user)
        node.save()
        for log in node.logs:
            if log.action == 'contributor_added':
                project.logs.append(log)
        project.save()

        node_list = get_targets()
        do_migration(node_list)

        logs = [each for each in project.logs if each.action == 'contributor_added']
        assert len(logs) is 1
        assert logs[0].should_hide is True
