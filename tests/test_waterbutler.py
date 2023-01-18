from unittest import mock
from unittest.mock import patch

from framework.auth import Auth
from osf.models import AbstractNode
from osf_tests.factories import ProjectFactory, OsfStorageFileFactory, InstitutionFactory, ResponseFactory
from tests.base import OsfTestCase
from website.util import waterbutler


class TestWaterbutler(OsfTestCase):

    def setUp(self):
        super(TestWaterbutler, self).setUp()

        self.node = ProjectFactory()
        self.user = self.node.creator
        self.auth = Auth(self.user)
        self.institution = InstitutionFactory.create(_id='vcu')
        self.institution.nodes.set([self.node])
        self.projects = self.institution.nodes.filter(category='project')
        self.projects__ids = self.projects.values_list('id', flat=True)
        self.object_id = self.projects__ids[0]
        self.target = AbstractNode(id=self.object_id)
        self.file_node = OsfStorageFileFactory.create(target_object_id=self.object_id, target=self.target)

    @patch('website.util.waterbutler.get_node_info')
    @patch('website.util.waterbutler.os.path.basename')
    def test_download_file_with_file_info_return_none_value(self, mock_os, mock_get_node_info):
        mock_get_node_info.return_value = None
        mock_os.return_value = 'test_path'
        res = waterbutler.download_file('token', self.file_node, 'test_path')
        assert res == None

    @patch('website.util.waterbutler.get_node_info')
    @patch('website.util.waterbutler.os.path.join')
    @patch('website.util.waterbutler.os.path.basename')
    def test_download_file_raise_exception(self, mock_os, mock_os_join, mock_get_node_info):
        with patch('website.util.waterbutler.requests', side_effect=Exception('mocked error')):
            res = waterbutler.download_file('fake_cookie', self.file_node, 'test_download_path')
            assert res == None

    @patch('website.util.waterbutler.get_node_info')
    @patch('website.util.waterbutler.os.path.basename')
    @patch('website.util.waterbutler.os.path.join')
    @patch('website.util.waterbutler.requests.get')
    @patch('website.util.waterbutler.waterbutler_api_url_for')
    @patch('website.util.waterbutler.shutil.copyfileobj')
    def test_download_file(self, mock_shutil, mock_waterbutler_api, mock_request, mock_os_join, mock_os, mock_get_node_info):
        mock_get_node_info.return_value = 'file node info'
        mock_os.return_value = 'test_path'
        mock_shutil.return_value = None
        mock_waterbutler_api.return_value = None
        mock_os_join.return_value = 'test_full_path'
        mock_request.return_value = ResponseFactory('raw_data')
        with mock.patch('builtins.open', mock.mock_open(read_data='data output')):
            res = waterbutler.download_file('fake_cookie', self.file_node, 'test_download_path')
            assert res == 'test_full_path'
