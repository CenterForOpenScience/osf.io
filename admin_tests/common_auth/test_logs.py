from tests.base import AdminTestCase

from osf_tests.factories import UserFactory
from osf.models.admin_log_entry import AdminLogEntry, update_admin_log


class TestUpdateAdminLog(AdminTestCase):
    def test_add_log(self):
        user = UserFactory()
        update_admin_log(user.id, 'dfqc2', 'This', 'log_added')
        assert AdminLogEntry.objects.count() == 1
        log = AdminLogEntry.objects.latest('action_time')
        assert log.user_id == user.id
