import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from admin.guids.views import GuidDetailView, GuidReassignView, GuidSearchView
from osf.migrations import update_admin_permissions
from osf.models import AdminLogEntry, Guid
from osf.models.admin_log_entry import REMOVE_GUID
from osf_tests.factories import AuthUserFactory, NodeFactory
from tests.base import AdminTestCase


def patch_messages(request):
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, 'session', 'session')
    setattr(request, '_messages', FallbackStorage(request))


def user_in_group(name):
    update_admin_permissions()
    user = AuthUserFactory()
    user.groups.add(Group.objects.get(name=name))
    return user


class TestGuidSearchView(AdminTestCase):
    def test_search_redirects_to_detail(self):
        request = RequestFactory().post(reverse('guids:search'), {'guid': 'ABCDE'})
        request.user = user_in_group('remove_guid')
        response = GuidSearchView.as_view()(request)
        assert response.status_code == 302
        assert response.url == reverse('guids:detail', kwargs={'guid': 'abcde'})

    def test_search_rejects_malformed_guid(self):
        request = RequestFactory().post(reverse('guids:search'), {'guid': 'abc-de'})
        request.user = user_in_group('remove_guid')
        response = GuidSearchView.as_view()(request)
        assert response.status_code == 200
        assert 'is not a valid guid' in response.context_data['form'].errors['guid'][0]

    def test_search_requires_view_guid(self):
        request = RequestFactory().get(reverse('guids:search'))
        request.user = user_in_group('osf_admin')
        with pytest.raises(PermissionDenied):
            GuidSearchView.as_view()(request)


class TestGuidDetailView(AdminTestCase):
    def test_unknown_guid_is_404(self):
        request = RequestFactory().get('/fake')
        request.user = user_in_group('remove_guid')
        with pytest.raises(Http404):
            GuidDetailView.as_view()(request, guid='zzzzz')

    def test_shows_referent_and_link(self):
        node = NodeFactory()
        request = RequestFactory().get('/fake')
        request.user = user_in_group('remove_guid')
        response = GuidDetailView.as_view()(request, guid=node._id)
        assert response.status_code == 200
        assert response.context_data['referent'] == node
        assert response.context_data['referent_url'] == reverse('nodes:node', kwargs={'guid': node._id})


class TestGuidDetailViewReferents(AdminTestCase):
    def _get(self, guid):
        request = RequestFactory().get('/fake')
        request.user = user_in_group('remove_guid')
        return GuidDetailView.as_view()(request, guid=guid)

    def test_preprint_is_found_but_not_reassignable(self):
        from osf_tests.factories import PreprintFactory
        preprint = PreprintFactory()
        response = self._get(preprint.get_guid()._id)
        assert response.context_data['referent_url'] == reverse('preprints:preprint', kwargs={'guid': preprint._id})
        assert response.context_data['can_reassign'] is False
        assert response.context_data['reassign_blocker']

    def test_registration_is_found_but_not_reassignable(self):
        from osf_tests.factories import RegistrationFactory
        registration = RegistrationFactory()
        response = self._get(registration._id)
        assert response.context_data['referent_url'] == reverse('nodes:node', kwargs={'guid': registration._id})
        assert response.context_data['can_reassign'] is False

    def test_file_links_to_target_and_is_reassignable(self):
        node = NodeFactory()
        file = node.get_addon('osfstorage').get_root().append_file('f.txt')
        guid = file.get_guid(create=True)._id
        response = self._get(guid)
        assert response.context_data['referent_url'] == reverse('nodes:node', kwargs={'guid': node._id})
        assert response.context_data['can_reassign'] is True

    def test_node_is_reassignable(self):
        response = self._get(NodeFactory()._id)
        assert response.context_data['can_reassign'] is True


class TestGuidReassignView(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.node = NodeFactory()
        self.url = reverse('guids:reassign', kwargs={'guid': self.node._id})

    def _post(self, user, data):
        request = RequestFactory().post(self.url, data)
        patch_messages(request)
        request.user = user
        return GuidReassignView.as_view()(request, guid=self.node._id)

    def test_requires_remove_guid_permission(self):
        for group in ('osf_admin', 'read_only'):
            with pytest.raises(PermissionDenied):
                self._post(user_in_group(group), {'justification': 'because'})
        assert Guid.objects.filter(_id=self.node._id).exists()

    def test_justification_is_required(self):
        old_id = self.node._id
        response = self._post(user_in_group('remove_guid'), {'justification': '  '})
        assert response.status_code == 302
        assert Guid.objects.filter(_id=old_id).exists()
        assert not AdminLogEntry.objects.filter(action_flag=REMOVE_GUID).exists()

    def test_reassign_writes_admin_log(self):
        old_id = self.node._id
        user = user_in_group('remove_guid')
        response = self._post(user, {'justification': 'Preprint recovery, ticket 1'})

        node = type(self.node).objects.get(pk=self.node.pk)
        assert node._id != old_id
        assert response.url == reverse('guids:detail', kwargs={'guid': node._id})
        assert not Guid.objects.filter(_id=old_id).exists()
        entry = AdminLogEntry.objects.get(action_flag=REMOVE_GUID)
        assert entry.object_id == old_id
        assert entry.user_id == user.id
        assert 'Preprint recovery, ticket 1' in entry.change_message
        assert node._id in entry.change_message

    def test_reassign_logs_warning_with_details(self):
        old_id = self.node._id
        user = user_in_group('remove_guid')
        with self.assertLogs('admin.guids.views', level='WARNING') as logs:
            self._post(user, {'justification': 'Preprint recovery, ticket 1'})

        node = type(self.node).objects.get(pk=self.node.pk)
        message = '\n'.join(logs.output)
        assert f'old_guid={old_id}' in message
        assert f'new_guid={node._id}' in message
        assert f'referent_pk={node.pk}' in message
        assert 'Preprint recovery, ticket 1' in message

    def test_preprint_guid_is_refused(self):
        from osf_tests.factories import PreprintFactory
        preprint = PreprintFactory()
        guid = preprint.get_guid()._id
        request = RequestFactory().post('/fake', {'justification': 'x'})
        patch_messages(request)
        request.user = user_in_group('remove_guid')
        response = GuidReassignView.as_view()(request, guid=guid)
        assert response.status_code == 302
        assert Guid.objects.filter(_id=guid).exists()
        assert not AdminLogEntry.objects.filter(action_flag=REMOVE_GUID).exists()


class TestRemoveGuidGroup(AdminTestCase):
    def test_group_is_separate_from_osf_admin(self):
        update_admin_permissions()
        codenames = set(Group.objects.get(name='remove_guid').permissions.values_list('codename', flat=True))
        assert codenames == {'view_guid', 'remove_guid'}
        admin_codenames = set(Group.objects.get(name='osf_admin').permissions.values_list('codename', flat=True))
        assert 'remove_guid' not in admin_codenames
        assert 'view_guid' not in admin_codenames
