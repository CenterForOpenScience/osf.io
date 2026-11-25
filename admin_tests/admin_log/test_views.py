import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from admin.admin_log.views import AdminLogEntryListView
from osf.migrations import update_admin_permissions
from osf.models.admin_log_entry import REMOVE_GUID, update_admin_log
from osf_tests.factories import AuthUserFactory
from tests.base import AdminTestCase


class TestAdminLogEntryListView(AdminTestCase):
    def setUp(self):
        super().setUp()
        update_admin_permissions()
        self.user = AuthUserFactory()

    def _get(self, user, query=''):
        request = RequestFactory().get(f'/fake{query}')
        request.user = user
        return AdminLogEntryListView.as_view()(request)

    def test_requires_permission(self):
        with pytest.raises(PermissionDenied):
            self._get(self.user)
        self.user.groups.add(Group.objects.get(name='read_only'))
        with pytest.raises(PermissionDenied):
            self._get(self.user)

    def test_lists_newest_first_and_paginates(self):
        self.user.groups.add(Group.objects.get(name='osf_admin'))
        for i in range(55):
            update_admin_log(self.user.id, f'obj{i}', 'Node', f'message {i}', action_flag=REMOVE_GUID)

        response = self._get(self.user)
        assert response.status_code == 200
        entries = list(response.context_data['entries'])
        assert len(entries) == 50
        assert entries[0].object_id == 'obj54'
        assert entries[0].action_label == 'Remove Guid'

        response = self._get(self.user, '?page=2')
        assert len(response.context_data['entries']) == 5
