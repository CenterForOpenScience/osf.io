import datetime
import pytz
import os
from api.timestamp.add_timestamp import AddTimestamp
from osf.models import RdmFileTimestamptokenVerifyResult, Guid
import shutil

from nose import tools as nt
from tests.base import ApiTestCase
from osf_tests.factories import ProjectFactory
from api_tests.utils import create_test_file
from framework.auth import Auth
from website.views import userkey_generation

class TestAddTimestamp(ApiTestCase):

    def setUp(self):
        super(TestAddTimestamp, self).setUp()

        self.project = ProjectFactory()
        self.node = self.project
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        self.auth_obj = Auth(user=self.project.creator)
        userkey_generation(self.user._id)

        # Refresh records from database; necessary for comparing dates
        self.project.reload()
        self.user.reload()

    def tearDown(self):
        from api.base import settings as api_settings
        from osf.models import RdmUserKey

        super(TestAddTimestamp, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        self.user.delete()

        rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
        os.remove(pvt_key_path)
        rdmuserkey_pvt_key.delete()

        rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
        os.remove(pub_key_path)
        rdmuserkey_pub_key.delete()

    def test_add_timestamp(self):
        ## create file_node
        filename = 'test_file_add_timestamp'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        current_datetime = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
        current_datetime_str = current_datetime.strftime("%Y%m%d%H%M%S%f")
        tmp_dir = 'tmp_{}_{}_{}'.format(self.user._id, file_node._id, current_datetime_str)
        os.mkdir(tmp_dir)

        ## create tmp_file (file_node)
        download_file_path = os.path.join(tmp_dir, filename)
        with open(download_file_path, "wb") as fout:
            fout.write("test_file_add_timestamp_context")

        ## add timestamp
        addTimestamp = AddTimestamp()
        ret = addTimestamp.add_timestamp(self.user._id, file_node._id, self.node._id, 'osfstorage', os.path.join('/', filename), download_file_path, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check add_timestamp func response
        nt.assert_equal(ret['verify_result'], 1)
        nt.assert_equal(ret['verify_result_title'], 'OK')

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 1)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.validation_user, osfuser_id)
