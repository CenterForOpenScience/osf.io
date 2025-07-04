import pytest
from unittest.mock import patch

from osf.models import NodeLog
from osf_tests.factories import ProjectFactory, UserFactory
from osf.tasks import log_gv_addon


@pytest.mark.django_db
class TestGVAddonLogs:

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    def test_log_gv_addon_add(self, user, node):
        initial_log_count = node.logs.count()

        node_url = f"http://localhost:5000/{node._id}/"
        user_url = f"http://localhost:5000/{user._id}/"
        addon_name = 'github'

        log_gv_addon(node_url=node_url, action=NodeLog.ADDON_ADDED, user_url=user_url, addon=addon_name)

        assert node.logs.count() == initial_log_count + 1

        log = node.logs.first()
        assert log.action == NodeLog.ADDON_ADDED
        assert log.user == user
        assert log.params['node'] == node._id
        assert log.params['project'] == node.parent_id
        assert log.params['addon'] == addon_name

    def test_log_gv_addon_remove(self, user, node):
        initial_log_count = node.logs.count()

        node_url = f"http://localhost:5000/{node._id}/"
        user_url = f"http://localhost:5000/{user._id}/"
        addon_name = 'github'

        log_gv_addon(node_url=node_url, action=NodeLog.ADDON_REMOVED, user_url=user_url, addon=addon_name)

        assert node.logs.count() == initial_log_count + 1

        log = node.logs.first()
        assert log.action == NodeLog.ADDON_REMOVED
        assert log.user == user
        assert log.params['node'] == node._id
        assert log.params['project'] == node.parent_id
        assert log.params['addon'] == addon_name

    def test_log_gv_addon_invalid_action(self, user, node):
        initial_log_count = node.logs.count()

        node_url = f"http://localhost:5000/{node._id}/"
        user_url = f"http://localhost:5000/{user._id}/"
        addon_name = 'github'

        log_gv_addon(node_url=node_url, action='INVALID_ACTION', user_url=user_url, addon=addon_name)

        assert node.logs.count() == initial_log_count

    def test_log_gv_addon_invalid_node(self, user):
        initial_log_count = NodeLog.objects.filter(user=user).count()

        node_url = 'http://localhost:5000/invalid/'
        user_url = f"http://localhost:5000/{user._id}/"
        addon_name = 'github'

        log_gv_addon(node_url=node_url, action=NodeLog.ADDON_ADDED, user_url=user_url, addon=addon_name)

        assert NodeLog.objects.filter(user=user).count() == initial_log_count

    def test_log_gv_addon_invalid_user(self, node):
        initial_log_count = node.logs.count()

        node_url = f"http://localhost:5000/{node._id}/"
        user_url = 'http://localhost:5000/invalid/'
        addon_name = 'github'

        log_gv_addon(node_url=node_url, action=NodeLog.ADDON_ADDED, user_url=user_url, addon=addon_name)

        assert node.logs.count() == initial_log_count

    @patch('osf.tasks.get_object_by_url')
    def test_log_gv_addon_url_parsing(self, mock_get_object, user, node):
        initial_log_count = node.logs.count()

        node_url = f"http://localhost:5000/{node._id}/"
        user_url = f"http://localhost:5000/{user._id}/"
        addon_name = 'github'

        mock_get_object.side_effect = lambda url, model: user if url == user_url else node

        log_gv_addon(node_url=node_url, action=NodeLog.ADDON_ADDED, user_url=user_url, addon=addon_name)

        assert mock_get_object.call_count == 2

        assert node.logs.count() == initial_log_count + 1
