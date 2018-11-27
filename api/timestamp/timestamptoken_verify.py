# -*- coding: utf-8 -*-
# timestamp token check
import datetime
from django.utils import timezone
import os.path
import os
import subprocess


from osf.models import AbstractNode, BaseFileNode, RdmFileTimestamptokenVerifyResult, Guid, RdmUserKey, OSFUser
from api.base import settings as api_settings

import logging
from api.base.rdmlogger import RdmLogger, rdmlog

logger = logging.getLogger(__name__)


class TimeStampTokenVerifyCheck:

    # get abstractNode
    def get_abstractNode(self, node_id):
        # get project name
        try:
            abstractNode = AbstractNode.objects.get(id=node_id)
        except Exception as err:
            logging.exception(err)
            abstractNode = None

        return abstractNode

    # get verify result
    def get_verifyResult(self, file_id, project_id, provider, path):
        try:
            if RdmFileTimestamptokenVerifyResult.objects.filter(file_id=file_id).exists():
                verifyResult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_id)
            else:
                verifyResult = None

        except Exception as err:
            logging.exception(err)
            verifyResult = None

        return verifyResult

    # get baseFileNode
    def get_baseFileNode(self, file_id):
        try:
            baseFileNode = BaseFileNode.objects.get(_id=file_id)
        except Exception as err:
            logging.exception(err)
            baseFileNode = None

        return baseFileNode

    # get baseFileNode filepath
    def get_filenameStruct(self, fsnode, fname):
        try:
            if fsnode.parent is not None:
                fname = self.get_filenameStruct(fsnode.parent, fname) + '/' + fsnode.name
            else:
                fname = fsnode.name
        except Exception as err:
            logging.exception(err)

        return fname

    def create_rdm_filetimestamptokenverify(self, file_id, project_id, provider, path,
                                        inspection_result_status, userid):

        userKey = RdmUserKey.objects.get(guid=userid, key_kind=api_settings.PUBLIC_KEY_VALUE)
        create_data = RdmFileTimestamptokenVerifyResult()
        create_data.file_id = file_id
        create_data.project_id = project_id
        create_data.provider = provider
        create_data.key_file_name = userKey.key_name
        create_data.path = path
        create_data.inspection_result_status = inspection_result_status
        create_data.validation_user = userid
        create_data.validation_date = timezone.now()
        create_data.create_user = userid
        create_data.create_date = timezone.now()

        return create_data

    # timestamp token check
    def timestamp_check(self, guid, file_id, project_id, provider, path, file_name, tmp_dir):

        userid = Guid.objects.get(_id=guid).object_id

        # get verify result
        verifyResult = self.get_verifyResult(file_id, project_id, provider, path)

        ret = 0
        operator_user = None
        operator_date = None
        verify_result_title = None

        try:
            # get file information, verifyresult table
            if provider == 'osfstorage':
                # 'osfstrage'
                baseFileNode = self.get_baseFileNode(file_id)
                if baseFileNode.is_deleted and not verifyResult:
                    # if file was deleted ,and verify result does not exists:
                    # update verifyResult:'FILE missing'
                    ret = api_settings.FILE_NOT_EXISTS
                    verify_result_title = api_settings.FILE_NOT_EXISTS_MSG  # 'FILE missing'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider,
                                                                       path, ret, userid)
                elif baseFileNode.is_deleted and verifyResult and not verifyResult.timestamp_token:
                    # if file does not exists ,and verify result does not exists in db:
                    # update verifyResult 'FILE missing(Unverify)'
                    verifyResult.inspection_result_status = api_settings.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    ret = api_settings.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verify_result_title = api_settings.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG  # 'FILE missing(Unverify)'
                elif baseFileNode.is_deleted and verifyResult:
                    # if file was deleted, and verify result exists in db:
                    # update verifyResult 'FILE missing(Unverify)'
                    verifyResult.inspection_result_status = api_settings.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    ret = api_settings.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_NO_DATA
                elif not baseFileNode.is_deleted and not verifyResult:
                    # if file was deleted, and verify result does not exists in db:
                    # update verifyResult 'TST missing(Unverify)'
                    ret = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG  # 'TST missing(Unverify)'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider,
                                                                            path, ret, userid)
                elif not baseFileNode.is_deleted and not verifyResult.timestamp_token:
                    # if file exists and  verifyResult.timestamp_token does not exists:
                    # update verifyResult 'TST missing(Retrieving Failed)'
                    verifyResult.inspection_result_status = api_settings.TIME_STAMP_TOKEN_NO_DATA
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    ret = api_settings.TIME_STAMP_TOKEN_NO_DATA
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG  # 'TST missing(Retrieving Failed)'
            else:
                # storage other than osfstorage:
                if not verifyResult:
                    # if file does not exists, and  verify result does not exists:
                    # update verifyResult 'TST missing(Unverify)'
                    ret = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG  # 'TST missing(Unverify)'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider,
                                                                             path, ret, userid)
                elif not verifyResult.timestamp_token:
                    # if timestamptoken does not exists:
                    # update verifyResult 'TST missing(Retrieving Failed)'
                    verifyResult.inspection_result_status = api_settings.TIME_STAMP_TOKEN_NO_DATA
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    ret = api_settings.TIME_STAMP_TOKEN_NO_DATA
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG  # 'TST missing(Retrieving Failed)'

            if ret == 0:
                timestamptoken_file = guid + '.tsr'
                timestamptoken_file_path = os.path.join(tmp_dir, timestamptoken_file)
                try:
                    with open(timestamptoken_file_path, 'wb') as fout:
                        fout.write(verifyResult.timestamp_token)

                except Exception as err:
                    raise err

                # verify timestamptoken and rootCA
                cmd = [api_settings.OPENSSL_MAIN_CMD, api_settings.OPENSSL_OPTION_TS, api_settings.OPENSSL_OPTION_VERIFY,
                       api_settings.OPENSSL_OPTION_DATA, file_name, api_settings.OPENSSL_OPTION_IN, timestamptoken_file_path,
                       api_settings.OPENSSL_OPTION_CAFILE, os.path.join(api_settings.KEY_SAVE_PATH, api_settings.VERIFY_ROOT_CERTIFICATE)]
                prc = subprocess.Popen(cmd, shell=False,
                                       stdin=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
                stdout_data, stderr_data = prc.communicate()
                ret = api_settings.TIME_STAMP_TOKEN_UNCHECKED
                if stdout_data.__str__().find(api_settings.OPENSSL_VERIFY_RESULT_OK) > -1:
                    ret = api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS_MSG  # 'OK'
                else:
                    ret = api_settings.TIME_STAMP_TOKEN_CHECK_NG
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_NG_MSG  # 'NG'
                verifyResult.inspection_result_status = ret
                verifyResult.validation_user = userid
                verifyResult.validation_date = timezone.now()

            if not verifyResult.update_user:
                verifyResult.update_user = None
                verifyResult.update_date = None
                operator_user = OSFUser.objects.get(id=verifyResult.create_user).fullname
                operator_date = verifyResult.create_date.strftime('%Y/%m/%d %H:%M:%S')
            else:
                operator_user = OSFUser.objects.get(id=verifyResult.update_user).fullname
                operator_date = verifyResult.update_date.strftime('%Y/%m/%d %H:%M:%S')

            verifyResult.save()
        except Exception as err:
            logging.exception(err)

        # RDMINFO: TimeStampVerify
        if provider == 'osfstorage':
            if not baseFileNode._path:
                filename = self.get_filenameStruct(baseFileNode, '')
            else:
                filename = baseFileNode._path
            filepath = baseFileNode.provider + filename
            abstractNode = self.get_abstractNode(baseFileNode.node_id)
        else:
            filepath = provider + path
            abstractNode = self.get_abstractNode(Guid.objects.get(_id=project_id).object_id)

        ## RDM Logger ##
        rdmlogger = RdmLogger(rdmlog, {})
        rdmlogger.info('RDM Project', RDMINFO='TimeStampVerify', result_status=ret, user=guid, project=abstractNode.title, file_path=filepath, file_id=file_id)
        return {'verify_result': ret, 'verify_result_title': verify_result_title,
                'operator_user': operator_user, 'operator_date': operator_date,
                'filepath': filepath}
