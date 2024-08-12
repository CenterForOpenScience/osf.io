import pytest
from osf.management.commands.fix_quickfiles_waterbutler_logs import (
    fix_quickfiles_waterbutler_logs,
)
from osf_tests.factories import ProjectFactory
from osf.models import NodeLog


@pytest.mark.django_db
class TestFixQuickFilesLogs:
    @pytest.fixture()
    def node(self):
        return ProjectFactory()

    @pytest.fixture()
    def node_log_files_added(self, node):
        return NodeLog(
            action="osf_storage_file_added",
            node=node,
            params={
                "contributors": [],
                "params_node": {
                    "id": "jpmxy",
                    "title": "John Tordoff's Quick Files",
                },
                "params_project": None,
                "path": "/test.json",
                "pointer": None,
                "preprint_provider": None,
                "urls": {
                    "view": f"/{node._id}/files/osfstorage/622aad8d1e399c0c296017b0/?pid={node._id}",
                    "download": f"/{node._id}/files/osfstorage/622aad8d1e399c0c296017b0/?pid={node._id}?action=download",
                },
            },
        ).save()

    @pytest.fixture()
    def node_log_files_renamed(self, node):
        return NodeLog(
            action="addon_file_renamed",
            node=node,
            params={
                "contributors": [],
                "destination": {
                    "materialized": "test-JATS1.xml",
                    "url": "/project/jpmxy/files/osfstorage/622aad914ef4bb0ac0333f9f/",
                    "addon": "OSF Storage",
                    "node_url": "/jpmxy/",
                    "resource": "jpmxy",
                    "node_title": "John Tordoff's Quick Files",
                },
                "params_node": {
                    "id": "jpmxy",
                    "title": "John Tordoff's Quick Files",
                },
                "params_project": None,
                "pointer": None,
                "preprint_provider": None,
                "source": {
                    "materialized": "test-JATS.xml",
                    "url": "/project/jpmxy/files/osfstorage/622aad914ef4bb0ac0333f9f/",
                    "addon": "OSF Storage",
                    "node_url": "/jpmxy/",
                    "resource": "jpmxy",
                    "node_title": "John Tordoff's Quick Files",
                },
            },
        ).save()

    @pytest.mark.enable_enqueue_task
    def test_fix_quickfiles_waterbutler_logs_files_added(
        self, node, node_log_files_added
    ):
        NodeLog(node=node, action=NodeLog.MIGRATED_QUICK_FILES).save()
        fix_quickfiles_waterbutler_logs()
        log = node.logs.all().get(action="osf_storage_file_added")
        guid = node.guids.last()._id

        assert log.params["urls"] == {
            "view": f"/{guid}/files/osfstorage/622aad8d1e399c0c296017b0/?pid={guid}",
            "download": f"/{guid}/files/osfstorage/622aad8d1e399c0c296017b0/?pid={guid}&action=download",
        }

    @pytest.mark.enable_enqueue_task
    def test_fix_quickfiles_waterbutler_logs_files_renamed(
        self, node, node_log_files_renamed
    ):
        NodeLog(node=node, action=NodeLog.MIGRATED_QUICK_FILES).save()
        fix_quickfiles_waterbutler_logs()
        log = node.logs.all().get(action="addon_file_renamed")
        guid = node.guids.last()._id

        assert (
            log.params["source"]["url"]
            == f"/project/{guid}/files/osfstorage/622aad914ef4bb0ac0333f9f/?pid={guid}"
        )
        assert (
            log.params["destination"]["url"]
            == f"/project/{guid}/files/osfstorage/622aad914ef4bb0ac0333f9f/?pid={guid}"
        )
        assert log.params["params_node"]["_id"] == guid
