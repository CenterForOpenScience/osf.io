from tests.base import AdminTestCase
from django.test import RequestFactory
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory
from admin.management import views
from admin_tests.utilities import setup_view
from osf.models import GuidMetadataRecord


class TestManagement(AdminTestCase):

    def setUp(self):
        self.project = ProjectFactory(is_public=True)
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.SetEmptyResourceTypeGeneralForDataarchiveRegistrations()
        self.view = setup_view(self.view, self.request)
        self.registration = RegistrationFactory(project=self.project, is_public=True)
        self.registration.provider._id = 'dataarchive'
        self.registration.provider.save()

    def test_dataarchive_registration_resource_type_management_command_set_with_empty_string_metadata_record_in_database(self):
        self.guid_metadata_record = GuidMetadataRecord(guid_id=self.registration.guids.first().id)
        self.guid_metadata_record.save()
        assert self.guid_metadata_record.resource_type_general == ''
        self.view.post(self.request)
        assert GuidMetadataRecord.objects.get(guid___id=self.registration._id).resource_type_general == 'Dataset'

    def test_dataarchive_registration_resource_type_management_command_set_with_no_metadata_record_in_database(
            self):
        self.view.post(self.request)
        assert GuidMetadataRecord.objects.filter(guid___id=self.registration._id).first() is None
