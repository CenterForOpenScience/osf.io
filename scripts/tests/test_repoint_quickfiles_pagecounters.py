import pytest
from scripts.repoint_quickfiles_pagecounters import rekey_pagecounters
from osf.models import QuickFilesNode, PageCounter, OSFUser
from osf.utils.testing.pytest_utils import MigrationTestCase


@pytest.mark.django_db
class TestRepointQuickfilesPagecounters(MigrationTestCase):

    number_of_quickfiles = 10
    number_of_users = 5

    @pytest.mark.parametrize('type', ['download', 'view'])
    def test_rekey_pagecounters_download(self, type, request_context):
        self.add_users(self.number_of_users, with_quickfiles_node=True)
        self.sprinkle_quickfiles(QuickFilesNode, self.number_of_quickfiles)
        self.sprinkle_pagecounters(type, 10)

        # canary user
        user = OSFUser.objects.last()
        qfn = QuickFilesNode.objects.get_for_user(user)
        page_counters = list(PageCounter.objects.filter(_id__startswith='{}:{}'.format(type, qfn._id)))

        rekey_pagecounters()

        assert PageCounter.objects.filter(_id__contains=qfn._id).count() == 0
        assert list(PageCounter.objects.filter(_id__contains=user._id)) == page_counters
