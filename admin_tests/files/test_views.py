import pytest
from unittest import mock

from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.urls import reverse

from addons.osfstorage import settings as osfstorage_settings
from admin.files.views import FileDeleteView, FileVersionDeleteView, FileView
from admin_tests.utilities import setup_log_view
from api_tests.utils import create_test_file
from osf.models import AdminLogEntry, BaseFileNode, FileVersion, NodeLog
from osf.models.files import BaseFileVersionsThrough, TrashedFile
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, PreprintFactory, ProjectFactory


def patch_messages(request):
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)


def add_permission(user, codename, model=BaseFileNode):
    permission = Permission.objects.filter(
        codename=codename,
        content_type_id=ContentType.objects.get_for_model(model).id
    ).first()
    user.user_permissions.add(permission)
    user.save()


def add_second_version(test_file, user):
    return test_file.create_version(user, {
        'object': 'second-object-id',
        'service': 'cloud',
        'bucket': 'us-bucket',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 42,
        'contentType': 'img/png',
    })


class TestFileDeleteView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.admin_user = AuthUserFactory()
        self.test_file = create_test_file(self.node, self.admin_user)
        self.guid = self.test_file.get_guid(create=True)._id
        self.request = RequestFactory().post('/fake_path')
        self.request.user = self.admin_user
        patch_messages(self.request)
        self.plain_view = FileDeleteView
        self.view = setup_log_view(self.plain_view(), self.request, guid=self.guid)
        self.url = reverse('files:file-delete', kwargs={'guid': self.guid})

    def test_delete_file(self):
        count = AdminLogEntry.objects.count()
        response = self.view.post(self.request)
        # `delete()` recasts the row to TrashedFile (TypedModels STI), so re-fetch
        # via the base manager instead of refresh_from_db() on the original typed instance.
        deleted_file = BaseFileNode.objects.get(id=self.test_file.id)
        assert isinstance(deleted_file, TrashedFile)
        assert AdminLogEntry.objects.count() == count + 1
        assert response.url == reverse('home')
        log = self.node.logs.filter(
            action=NodeLog.FILE_REMOVED,
            foreign_user=NodeLog.SUPPORT_USER_LABEL,
        ).latest('date')
        assert log.user is None
        assert log.foreign_user == NodeLog.SUPPORT_USER_LABEL

    def test_delete_already_trashed_file_is_noop(self):
        self.test_file.delete(user=self.admin_user)
        count = AdminLogEntry.objects.count()
        response = self.view.post(self.request)
        assert AdminLogEntry.objects.count() == count
        assert response.url == reverse('files:file', kwargs={'guid': self.guid})

    def test_delete_checked_out_file_blocked(self):
        self.test_file.checkout = self.admin_user
        self.test_file.save()
        count = AdminLogEntry.objects.count()
        response = self.view.post(self.request)
        self.test_file.refresh_from_db()
        assert not isinstance(self.test_file, TrashedFile)
        assert AdminLogEntry.objects.count() == count
        assert response.url == reverse('files:file', kwargs={'guid': self.guid})

    def test_delete_preprint_primary_file_blocked(self):
        preprint = PreprintFactory()
        primary_file = preprint.primary_file
        primary_file_guid = primary_file.get_guid(create=True)._id
        view = setup_log_view(self.plain_view(), self.request, guid=primary_file_guid)
        count = AdminLogEntry.objects.count()
        response = view.post(self.request)
        primary_file.refresh_from_db()
        assert not isinstance(primary_file, TrashedFile)
        assert AdminLogEntry.objects.count() == count
        assert response.url == reverse('files:file', kwargs={'guid': primary_file_guid})

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().post(self.url)
        request.user = user

        with pytest.raises(PermissionDenied):
            self.plain_view.as_view()(request, guid=self.guid)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        add_permission(user, 'delete_basefilenode')
        add_permission(user, 'view_basefilenode')

        request = RequestFactory().post(self.url)
        patch_messages(request)
        request.user = user

        response = self.plain_view.as_view()(request, guid=self.guid)
        assert response.status_code == 302


class TestFileVersionDeleteView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.admin_user = AuthUserFactory()
        self.test_file = create_test_file(self.node, self.admin_user)
        self.guid = self.test_file.get_guid(create=True)._id
        self.first_version = self.test_file.versions.first()
        self.request = RequestFactory().post('/fake_path')
        self.request.user = self.admin_user
        patch_messages(self.request)
        self.plain_view = FileVersionDeleteView

    def _make_view(self, version_id):
        return setup_log_view(
            self.plain_view(), self.request,
            guid=self.guid, version_id=version_id,
        )

    def test_delete_version_unlinks_and_enqueues_purge(self):
        second_version = add_second_version(self.test_file, self.admin_user)
        view = self._make_view(self.first_version._id)
        count = AdminLogEntry.objects.count()

        with mock.patch('admin.files.views.enqueue_postcommit_task') as mock_enqueue:
            view.post(self.request)

        assert not BaseFileVersionsThrough.objects.filter(
            basefilenode=self.test_file, fileversion=self.first_version
        ).exists()
        assert BaseFileVersionsThrough.objects.filter(
            basefilenode=self.test_file, fileversion=second_version
        ).exists()
        mock_enqueue.assert_called_once()
        assert mock_enqueue.call_args[0][1] == (self.first_version.pk,)
        assert AdminLogEntry.objects.count() == count + 1

    def test_cannot_delete_sole_version(self):
        view = self._make_view(self.first_version._id)
        count = AdminLogEntry.objects.count()

        with mock.patch('admin.files.views.enqueue_postcommit_task') as mock_enqueue:
            view.post(self.request)

        assert BaseFileVersionsThrough.objects.filter(
            basefilenode=self.test_file, fileversion=self.first_version
        ).exists()
        mock_enqueue.assert_not_called()
        assert AdminLogEntry.objects.count() == count

    def test_version_belonging_to_different_file_blocked(self):
        other_file = create_test_file(self.node, self.admin_user, filename='other_file')
        add_second_version(self.test_file, self.admin_user)
        view = self._make_view(other_file.versions.first()._id)
        count = AdminLogEntry.objects.count()

        with mock.patch('admin.files.views.enqueue_postcommit_task') as mock_enqueue:
            view.post(self.request)

        mock_enqueue.assert_not_called()
        assert AdminLogEntry.objects.count() == count

    def test_no_user_permissions_raises_error(self):
        add_second_version(self.test_file, self.admin_user)
        user = AuthUserFactory()
        url = reverse('files:file-version-delete', kwargs={
            'guid': self.guid, 'version_id': self.first_version._id,
        })
        request = RequestFactory().post(url)
        request.user = user

        with pytest.raises(PermissionDenied):
            self.plain_view.as_view()(request, guid=self.guid, version_id=self.first_version._id)

    def test_correct_view_permissions(self):
        add_second_version(self.test_file, self.admin_user)
        user = AuthUserFactory()
        add_permission(user, 'delete_fileversion', model=FileVersion)
        add_permission(user, 'view_basefilenode')

        url = reverse('files:file-version-delete', kwargs={
            'guid': self.guid, 'version_id': self.first_version._id,
        })
        request = RequestFactory().post(url)
        patch_messages(request)
        request.user = user

        response = self.plain_view.as_view()(request, guid=self.guid, version_id=self.first_version._id)
        assert response.status_code == 302


class TestFileViewVersionSelection(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.user = AuthUserFactory()
        add_permission(self.user, 'view_basefilenode')
        self.test_file = create_test_file(self.node, self.user)
        self.guid = self.test_file.get_guid(create=True)._id
        self.first_version = self.test_file.versions.first()
        self.second_version = add_second_version(self.test_file, self.user)

    def _get_context(self, query_string=''):
        url = reverse('files:file', kwargs={'guid': self.guid}) + query_string
        request = RequestFactory().get(url)
        request.user = self.user
        response = FileView.as_view()(request, guid=self.guid)
        return response.context_data

    def test_defaults_to_latest_version(self):
        context = self._get_context()
        assert context['selected_version'].pk == self.second_version.pk

    def test_selecting_specific_version_via_query_param(self):
        context = self._get_context(f'?version={self.first_version._id}')
        assert context['selected_version'].pk == self.first_version.pk

    def test_invalid_version_falls_back_to_latest(self):
        context = self._get_context('?version=does-not-exist')
        assert context['selected_version'].pk == self.second_version.pk
