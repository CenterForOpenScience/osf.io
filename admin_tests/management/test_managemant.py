from tests.base import AdminTestCase
from django.test import RequestFactory
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory
from admin.management import views
from admin_tests.utilities import setup_view
from osf.models import Guid, GuidMetadataRecord


class TestManagement(AdminTestCase):

    def setUp(self):
        self.project = ProjectFactory(is_public=True)
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.SetEmptyResourceTypeGeneralForDataarchiveRegistrations()
        self.view = setup_view(self.view, self.request, user_id=self.user._id)
        self.registration = RegistrationFactory(project=self.project, is_public=True)
        self.registration.provider._id = 'dataarchive'
        self.registration.provider.save()

    def test_dataarchive_registration_resource_type_general_management_command_set_with_no_metadata(self):
        self.view.post(self.request)
        assert GuidMetadataRecord.objects.get(guid___id=self.registration._id).resource_type_general == 'Dataset'

    def test_dataarchive_registration_resource_type_general_management_command_set_with_metadata(self):
        guid = Guid.objects.get(_id=self.registration._id)
        guid_metadata_record = GuidMetadataRecord(guid_id=guid.id, resource_type_general='Book')
        guid_metadata_record.save()
        self.view.post(self.request)
        assert GuidMetadataRecord.objects.get(guid_id=guid.id).resource_type_general == 'Book'
