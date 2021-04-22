# -*- coding: utf-8 -*-
import datetime
import mock
import os
import pytz
import shutil
from addons.osfstorage import settings as osfstorage_settings
from api.base import settings as api_settings
from framework.auth import Auth
from nose import tools as nt
from osf.models import RdmUserKey, RdmFileTimestamptokenVerifyResult, Guid
from osf_tests.factories import ProjectFactory, AuthUserFactory
from tests.base import ApiTestCase, OsfTestCase
from website.util import timestamp
import tempfile
from website.util.timestamp import (
    AddTimestamp, TimeStampTokenVerifyCheck,
    userkey_generation, userkey_generation_check,
    OSFAbortableAsyncResult
)


def create_test_file(node, user, filename='test_file', create_guid=True):
    osfstorage = node.get_addon('osfstorage')
    root_node = osfstorage.get_root()
    test_file = root_node.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 1337,
        'contentType': 'img/png'
    }).save()
    return test_file

def create_rdmfiletimestamptokenverifyresult(self, filename='test_file_timestamp_check', provider='osfstorage', inspection_result_status_1=True):
    ## create file_node(BaseFileNode record)
    file_node = create_test_file(node=self.node, user=self.user, filename=filename)
    file_node.save()
    ## create tmp_dir
    tmp_dir = tempfile.mkdtemp()

    ## create tmp_file (file_node)
    tmp_file = os.path.join(tmp_dir, filename)
    with open(tmp_file, 'wb') as fout:
        fout.write('filename:{}, provider:{}, inspection_result_status_1(true:1 or false:3):{}'.format(filename, provider, inspection_result_status_1).encode('utf-8'))
    if inspection_result_status_1:
        ## add timestamp
        addTimestamp = AddTimestamp()
        file_data = {
            'file_id': file_node._id,
            'file_name': 'Hello.txt',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': None,
            'modified': None,
            'version': '',
            'provider': provider
        }
        ret = addTimestamp.add_timestamp(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
    else:
        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': '',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
    shutil.rmtree(tmp_dir)

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
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        download_file_path = os.path.join(tmp_dir, filename)
        with open(download_file_path, 'wb') as fout:
            fout.write(b'test_file_add_timestamp_context')

        ## add timestamp
        addTimestamp = AddTimestamp()
        file_data = {
            'file_id': file_node._id,
            'file_name': 'Hello World.txt',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': None,
            'modified': None,
            'version': '',
            'provider': 'osfstorage'
        }
        ret = addTimestamp.add_timestamp(self.user._id, file_data, self.node._id, download_file_path, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check add_timestamp func response
        nt.assert_equal(ret['verify_result'], 1)
        nt.assert_equal(ret['verify_result_title'], 'OK')

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 1)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_add_timestamp_cjkname(self):
        ## create file_node
        filename = '𩸽.txt'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        download_file_path = os.path.join(tmp_dir, filename)
        with open(download_file_path, 'wb') as fout:
            fout.write(b'test_file_add_timestamp_context')
        ## add timestamp
        addTimestamp = AddTimestamp()
        file_data = {
            'file_id': file_node._id,
            'file_name': '𩸽.txt',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': None,
            'modified': None,
            'version': '',
            'provider': 'osfstorage'
        }
        ret = addTimestamp.add_timestamp(self.user._id, file_data, self.node._id, download_file_path, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check add_timestamp func response
        nt.assert_equal(ret['verify_result'], 1)
        nt.assert_equal(ret['verify_result_title'], 'OK')

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 1)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_add_timestamp_over2G(self):
        ## create file_node
        filename = 'test_file_add_timestamp'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        current_datetime = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
        current_datetime_str = current_datetime.strftime('%Y%m%d%H%M%S%f')
        tmp_dir = 'tmp_{}_{}_{}'.format(self.user._id, file_node._id, current_datetime_str)
        os.mkdir(tmp_dir)

        ## create tmp_file (file_node)
        download_file_path = os.path.join(tmp_dir, filename)
        with open(download_file_path, 'wb') as fout:
            fout.write(b'test_file_add_timestamp_context')

        ## add timestamp
        addTimestamp = AddTimestamp()
        file_data = {
            'file_id': file_node._id,
            'file_name': 'Hello.txt',
            'file_path': os.path.join('/', filename),
            'size': 21474836480,
            'created': None,
            'modified': None,
            'version': '',
            'provider': 'osfstorage'
        }
        ret = addTimestamp.add_timestamp(self.user._id, file_data, self.node._id, download_file_path, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check add_timestamp func response
        nt.assert_equal(ret['verify_result'], 1)
        nt.assert_equal(ret['verify_result_title'], 'OK')

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 1)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

class TestTimeStampTokenVerifyCheck(ApiTestCase):
    def setUp(self):
        super(TestTimeStampTokenVerifyCheck, self).setUp()

        self.project = ProjectFactory()
        self.node = self.project
        self.user = self.project.creator
        self.auth_obj = Auth(user=self.project.creator)
        userkey_generation(self.user._id)

        # Refresh records from database; necessary for comparing dates
        self.project.reload()
        self.user.reload()

    def tearDown(self):
        from osf.models import RdmUserKey

        super(TestTimeStampTokenVerifyCheck, self).tearDown()
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

    def test_timestamp_check_return_status_1(self):
        """
        TIME_STAMP_TOKEN_CHECK_SUCCESS = 1
        TIME_STAMP_TOKEN_CHECK_SUCCESS_MSG = 'OK'
        """
        provider = 'osfstorage'
        self.node_settings = self.project.get_addon(provider)

        ## create file_node(BaseFileNode record)
        filename = 'test_file_timestamp_check'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        tmp_file = os.path.join(tmp_dir, filename)
        with open(tmp_file, 'wb') as fout:
            fout.write(b'test_file_timestamp_check_context')

        ## add timestamp
        addTimestamp = AddTimestamp()
        file_data = {
            'file_id': file_node._id,
            'file_name': 'Hello.txt',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': None,
            'modified': None,
            'version': '',
            'provider': provider
        }
        addTimestamp.add_timestamp(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)

        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': 'Hello.txt',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check timestamp_check func response
        nt.assert_equal(ret['verify_result'], 1)
        nt.assert_equal(ret['verify_result_title'], 'OK')

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 1)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_timestamp_check_return_status_2(self):
        """
        [IN & Testdata]
         RdmFileTimestamptokenVerifyResult : Exist & RdmFileTimestamptokenVerifyResult.timestamp_token != null
         provider = 's3'
         * File(tmp_file) update from outside the system
        [OUT]
          TIME_STAMP_TOKEN_CHECK_NG = 2
          TIME_STAMP_TOKEN_CHECK_NG_MSG = 'NG'
        """
        provider = 's3'
        self.node_settings = self.project.get_addon(provider)

        ## create file_node(BaseFileNode record)
        filename = 'test_file_timestamp_check'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        tmp_file = os.path.join(tmp_dir, filename)
        with open(tmp_file, 'wb') as fout:
            fout.write(b'test_timestamp_check_return_status_2.test_file_context')

        ## add timestamp
        addTimestamp = AddTimestamp()
        file_data = {
            'file_id': file_node._id,
            'file_name': 'Hello.txt',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': None,
            'modified': None,
            'version': '',
            'provider': provider
        }
        addTimestamp.add_timestamp(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)

        ## File(tmp_file) update from outside the system
        with open(tmp_file, 'wb') as fout:
            fout.write(b'test_timestamp_check_return_status_2.test_file_context...File(tmp_file) update from outside the system.')

        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': '',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check timestamp_check func response
        nt.assert_equal(ret['verify_result'], api_settings.TIME_STAMP_TOKEN_CHECK_NG)
        nt.assert_equal(ret['verify_result_title'], api_settings.TIME_STAMP_TOKEN_CHECK_NG_MSG)

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 2)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_timestamp_check_return_status_3(self):
        """
        [IN & Testdata]
         BaseFileNode : Exist
         RdmFileTimestamptokenVerifyResult : None
         provider = 'osfstorage'
        [OUT]
         TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND = 3
         TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG = 'TST missing(Unverify)'
        """
        provider = 'osfstorage'
        self.node_settings = self.project.get_addon(provider)

        ## create file_node(BaseFileNode record)
        filename = 'test_file_timestamp_check'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        tmp_file = os.path.join(tmp_dir, filename)
        with open(tmp_file, 'wb') as fout:
            fout.write(b'test_file_timestamp_check_context')

        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': '',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check timestamp_check func response
        nt.assert_equal(ret['verify_result'], api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND)
        nt.assert_equal(ret['verify_result_title'], api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG)

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 3)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_timestamp_check_return_status_4(self):
        """
        [IN & Testdata]
         BaseFileNode : Exist & BaseFileNode.is_deleted = False
         RdmFileTimestamptokenVerifyResult : Exist & RdmFileTimestamptokenVerifyResult.timestamp_token = null
         provider = 'osfstorage'
        [OUT]
         TIME_STAMP_TOKEN_NO_DATA = 4
         TIME_STAMP_TOKEN_NO_DATA_MSG = 'TST missing(Retrieving Failed)'
        """
        provider = 'osfstorage'
        self.node_settings = self.project.get_addon(provider)

        ## create file_node(BaseFileNode record)
        filename = 'test_file_timestamp_check'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        tmp_file = os.path.join(tmp_dir, filename)

        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': '',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        # Yes, checking twice is necessary. Don't ask me the reason
        verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check timestamp_check func response
        nt.assert_equal(ret['verify_result'], api_settings.TIME_STAMP_TOKEN_NO_DATA)
        nt.assert_equal(ret['verify_result_title'], api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG)

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 4)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_timestamp_check_return_status_5(self):
        """
        [IN & Testdata]
         BaseFileNode : Exist & BaseFileNode.is_deleted = True
         RdmFileTimestamptokenVerifyResult : None
         provider = 'osfstorage'
        [OUT]
         FILE_NOT_EXISTS = 5
         FILE_NOT_EXISTS_MSG = 'FILE missing'
        """
        provider = 'osfstorage'
        self.node_settings = self.project.get_addon(provider)

        ## create file_node(BaseFileNode record)
        filename = 'test_file_timestamp_check'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)
        file_node.delete()

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        tmp_file = os.path.join(tmp_dir, filename)

        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': '',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check timestamp_check func response
        nt.assert_equal(ret['verify_result'], api_settings.FILE_NOT_EXISTS)
        nt.assert_equal(ret['verify_result_title'], api_settings.FILE_NOT_EXISTS_MSG)

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 5)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)

    def test_timestamp_check_return_status_6(self):
        """
        [IN & Testdata]
         BaseFileNode : Exist & BaseFileNode.is_deleted = True
         RdmFileTimestamptokenVerifyResult : Exist & RdmFileTimestamptokenVerifyResult.timestamp_token = null
         provider = 'osfstorage'
        [OUT]
         FILE_NOT_FOUND = 6
         FILE_NOT_FOUND_MSG = 'FILE missing(Unverify)'
        """
        provider = 'osfstorage'
        self.node_settings = self.project.get_addon(provider)

        ## create file_node(BaseFileNode record)
        filename = 'test_file_timestamp_check'
        file_node = create_test_file(node=self.node, user=self.user, filename=filename)
        file_node.delete()

        ## create tmp_dir
        tmp_dir = tempfile.mkdtemp()

        ## create tmp_file (file_node)
        tmp_file = os.path.join(tmp_dir, filename)

        ## verify timestamptoken
        verifyCheck = TimeStampTokenVerifyCheck()
        file_data = {
            'file_id': file_node._id,
            'file_name': '',
            'file_path': os.path.join('/', filename),
            'size': 1234,
            'created': '',
            'modified': '',
            'version': '',
            'provider': provider
        }
        # Yes, checking twice is necessary. Don't ask me the reason
        verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        ret = verifyCheck.timestamp_check(self.user._id, file_data, self.node._id, tmp_file, tmp_dir)
        shutil.rmtree(tmp_dir)

        ## check timestamp_check func response
        nt.assert_equal(ret['verify_result'], api_settings.FILE_NOT_FOUND)
        nt.assert_equal(ret['verify_result_title'], api_settings.FILE_NOT_FOUND_MSG)

        ## check rdmfiletimestamptokenverifyresult record
        rdmfiletimestamptokenverifyresult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        nt.assert_equal(rdmfiletimestamptokenverifyresult.inspection_result_status, 6)
        nt.assert_equal(rdmfiletimestamptokenverifyresult.verify_user, osfuser_id)


class TestRdmUserKey(OsfTestCase):
    def setUp(self):
        super(TestRdmUserKey, self).setUp()
        self.user = AuthUserFactory()

    def tearDown(self):
        super(TestRdmUserKey, self).tearDown()
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id

        key_exists_check = userkey_generation_check(self.user._id)
        if key_exists_check:
            rdmuserkey_pvt_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
            pvt_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pvt_key.key_name)
            os.remove(pvt_key_path)
            rdmuserkey_pvt_key.delete()

            rdmuserkey_pub_key = RdmUserKey.objects.get(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
            pub_key_path = os.path.join(api_settings.KEY_SAVE_PATH, rdmuserkey_pub_key.key_name)
            os.remove(pub_key_path)
            rdmuserkey_pub_key.delete()
        self.user.delete()

    def test_userkey_generation_check_return_true(self):
        userkey_generation(self.user._id)
        nt.assert_true(userkey_generation_check(self.user._id))

    def test_userkey_generation_check_return_false(self):
        nt.assert_false(userkey_generation_check(self.user._id))

    def test_userkey_generation(self):
        osfuser_id = Guid.objects.get(_id=self.user._id).object_id
        userkey_generation(self.user._id)

        rdmuserkey_pvt_key = RdmUserKey.objects.filter(guid=osfuser_id, key_kind=api_settings.PRIVATE_KEY_VALUE)
        nt.assert_equal(rdmuserkey_pvt_key.count(), 1)

        rdmuserkey_pub_key = RdmUserKey.objects.filter(guid=osfuser_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        nt.assert_equal(rdmuserkey_pub_key.count(), 1)


class TestOSFAbortableResult(OsfTestCase):

    @mock.patch('celery.contrib.abortable.AbortableAsyncResult.ready')
    def test_ready_succeed(self, mock_ready):
        mock_ready.return_value = False

        task = OSFAbortableAsyncResult('taskid')
        nt.assert_false(task.ready())

    @mock.patch('website.util.timestamp.logger')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult.ready')
    def test_ready_raise_attribute_error(self, mock_ready, mock_logger):
        msg = '\'module\' object has no attribute \'MultipleObjectsReturned\''
        mock_ready.side_effect = AttributeError(msg)

        task = OSFAbortableAsyncResult('taskid')
        nt.assert_true(task.ready())
        mock_logger.error.assert_any_call('Failed to get task status! Exception message:')
        mock_logger.error.assert_any_call(msg)
