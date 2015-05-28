from website.models import Node
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, NodeFactory
from scripts.migrate_logs_fix import (
    do_migration, get_targets
)


class TestMigrateLogs(OsfTestCase):

    def tearDown(self):
        OsfTestCase.tearDown(self)
        Node.remove()

    def test_get_targets(self):
        project1 = ProjectFactory()
        for log in project1.logs:
            log.should_hide = True
            log.save()
        project1.save()

        list = get_targets()
        assert list is not None
        assert len(list) is 1

    def test_do_migration(self):
        project = ProjectFactory()
        user = UserFactory()
        node = NodeFactory(parent=project)
        node.add_contributor(contributor=user)
        node.save()
        for log in node.logs:
            if log.action == 'contributor_added':
                log.should_hide = True
                log.save()
                project.logs.append(log)
        project.save()

        list = get_targets()
        do_migration(list)

        logs = [each for each in project.logs if each.action == 'contributor_added']
        assert len(logs) is 0

        logs2 = [each for each in node.logs if each.action == 'contributor_added']
        assert logs2[0].should_hide is False
