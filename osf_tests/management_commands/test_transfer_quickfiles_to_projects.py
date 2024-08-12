import pytest

from api_tests.utils import create_test_file

from osf.management.commands.transfer_quickfiles_to_projects import (
    remove_quickfiles,
    reverse_remove_quickfiles,
    QUICKFILES_DESC,
)
from osf.models import NodeLog
from osf.models.quickfiles import QuickFilesNode, get_quickfiles_project_title

from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestTransferQuickfilesToProjects:
    @pytest.fixture()
    def user_with_quickfiles(self):
        user = AuthUserFactory()
        qfnode = QuickFilesNode.objects.create_for_user(user)
        create_test_file(target=qfnode, user=user)
        return user

    def test_tranfer_quickfiles_to_projects(self, user_with_quickfiles):
        remove_quickfiles()

        assert not QuickFilesNode.objects.all()
        node = user_with_quickfiles.nodes.get(
            title=get_quickfiles_project_title(user_with_quickfiles),
            logs__action=NodeLog.MIGRATED_QUICK_FILES,
            description=QUICKFILES_DESC,
        )
        assert node.files.all()

    def test_reverse_tranfer_quickfiles_to_projects(
        self, user_with_quickfiles
    ):
        remove_quickfiles()
        reverse_remove_quickfiles()

        quickfiles_node = QuickFilesNode.objects.get_for_user(
            user_with_quickfiles
        )
        assert QuickFilesNode.objects.all().get() == quickfiles_node
        assert quickfiles_node.files.exists()
