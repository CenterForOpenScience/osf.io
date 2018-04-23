# -*- coding: utf-8 -*-
# timestamp token check
import datetime
import os.path
import os
import subprocess

#from modularodm import Q
#from modularodm.exceptions import NoResultsFound
#from modularodm.exceptions import ValidationValueError

from osf.models import AbstractNode, BaseFileNode, RdmFileTimestamptokenVerifyResult, Guid, RdmUserKey, OSFUser
from osf.utils import requests
from . import local

import logging
from api.base.rdmlogger import RdmLogger, rdmlog 
#from api.timestamp.rdmlogger import RdmLogger, rdmlog 

logger = logging.getLogger(__name__)


class TimeStampTokenVerifyCheck:

    # abstractNodeデータ取得
    def get_abstractNode(self, node_id):
        # プロジェクト名取得
        try:
            #abstractNode = AbstractNode.find_one(Q('id', 'eq', node_id))
            abstractNode = AbstractNode.objects.get(id=node_id) 
        except Exception as err:
            logging.exception(err)
            abstractNode = None

        return abstractNode

    # 検証結果データ取得
    def get_verifyResult(self, file_id, project_id, provider, path):
        # 検証結果取得
        try:
            if provider == 'osfstorage':
                #verifyResult = RdmFileTimestamptokenVerifyResult.find_one(Q('file_id', 'eq', file_id))
                verifyResult = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_id)
            else:
                if RdmFileTimestamptokenVerifyResult.objects.filter(project_id=project_id,
                                                            provider=provider,
                                                            path=path).exists():
                    verifyResult = RdmFileTimestamptokenVerifyResult.objects.get(project_id=project_id, 
                                                                                 provider=provider, 
                                                                                 path=path)
                else:
                    verifyResult = None

        except Exception as err:
            logging.exception(err)
            verifyResult = None

        return verifyResult

    # baseFileNodeデータ取得
    def get_baseFileNode(self, file_id):
        # ファイル取得
        try:
            #baseFileNode = BaseFileNode.find_one(Q('_id', 'eq', file_id))
            baseFileNode = BaseFileNode.objects.get(_id=file_id)
        except Exception as err:
            logging.exception(err)
            baseFileNode = None

        return baseFileNode

    # baseFileNodeのファイルパス取得
    def get_filenameStruct(self, fsnode, fname):
        try:
            if fsnode.parent is not None:
                 #fname = self.get_filenameStruct(self.get_baseFileNode(fsnode.parent_id), fname) + fsnode.name
                 fname = self.get_filenameStruct(fsnode.parent, fname) + "/" + fsnode.name
            else:
                 fname = fsnode.name
        except Exception as err:
            logging.exception(err)

        return fname

    def create_rdm_filetimestamptokenverify(self, file_id, project_id, provider, path, 
                                        inspection_result_status, userid):

        userKey = RdmUserKey.objects.get(guid=userid, key_kind=local.PUBLIC_KEY_VALUE)
        create_data = RdmFileTimestamptokenVerifyResult()
        if provider == 'osfstorage':
           create_data.file_id = file_id
        else:
           create_data.file_id = 'file_id_dummy'
        create_data.project_id = project_id
        create_data.provider = provider
        create_data.key_file_name = userKey.key_name
        create_data.path = path
        create_data.inspection_result_status = local.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
        create_data.validation_user = userid
        create_data.validation_date = datetime.datetime.now()
        create_data.create_user = userid
        create_data.create_date = datetime.datetime.now()

        return create_data

    # タイムスタンプトークンチェック
    def timestamp_check(self, guid, file_id, project_id, provider, path, file_name, tmp_dir):

#        logger.info('timestamp_check start guid:{guid} project_id:{project_id} provider:{provider} path:{path}'.format(guid=guid,
#                                                                                                                project_id=project_id,
#                                                                                                                provider=provider,
#                                                                                                                path=path))
        #userid = Guid.find_one(Q('_id', 'eq', guid)).object_id
        userid = Guid.objects.get(_id= guid).object_id

        # ファイル取得
        baseFileNode = self.get_baseFileNode(file_id)
        # 検証結果取得
        verifyResult = self.get_verifyResult(file_id, project_id, provider, path)

        ret = 0
        operator_user = None
        operator_date = None
        verify_result_title = None

        try:
            # ファイル情報と検証結果のタイムスタンプ未登録確認
            if provider == 'osfstorage':
                if baseFileNode and not verifyResult:
                    # ファイルが存在せず、検証結果がない場合
                    ret = local.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verify_result_title = 'NOT TIMESTAMP_VERIFY'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider, 
                                                                            path, ret, userid)
                elif baseFileNode.is_deleted and not verifyResult:
                    # ファイルが削除されていて検証結果がない場合
                    ret = local.FILE_NOT_EXISTS
                    verify_result_title = 'FILE_NOT_EXISTS'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider, 
                                                                       path, ret, userid)
                elif baseFileNode.is_deleted and verifyResult and not verifyResult.timestamp_token:
                    # ファイルが存在しなくてタイムスタンプトークンが未検証がない場合
                    verifyResult.inspection_result_status = local.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    ret = local.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_NO_DATA
                    verify_result_title = 'FILE_NOT_FOUND_AND_NOT_TIMESTAMP_VERIFY'
                elif baseFileNode.is_deleted and verifyResult:
                    # ファイルが削除されていて、検証結果テーブルにレコードが存在する場合
                    verifyResult.inspection_result_status = local.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    # ファイルが削除されていて検証結果があり場合、検証結果テーブルを更新する。
                    ret = local.FILE_NOT_EXISTS_TIME_STAMP_TOKEN_NO_DATA
                elif not baseFileNode.is_deleted and not verifyResult:
                    # ファイルは存在し、検証結果のタイムスタンプが未登録の場合は更新する。
                    ret = local.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verify_result_title = 'NOT TIMESTAMP_VERIFY'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider, 
                                                                            path, ret, userid)

                elif not baseFileNode.is_deleted and not verifyResult.timestamp_token:
                    # ファイルは存在し、検証結果のタイムスタンプが未登録の場合は更新する。
                    verifyResult.inspection_result_status = local.TIME_STAMP_TOKEN_NO_DATA
                    verifyResult.validation_user = userid
                    verifyResult.validation_date = datetime.datetime.now()
                    # ファイルが削除されていて検証結果があり場合、検証結果テーブルを更新する。
                    ret = local.TIME_STAMP_TOKEN_NO_DATA
                    verify_result_title = 'NOT TIMESTAMP_TOKEN'
            else:
                if not verifyResult:
                    # ファイルが存在せず、検証結果がない場合
                    ret = local.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                    verify_result_title = 'NOT TIMESTAMP_VERIFY'
                    verifyResult = self.create_rdm_filetimestamptokenverify(file_id, project_id, provider,
                                                                             path, ret, userid)
                elif not verifyResult.timestamp_token:
                     verifyResult.inspection_result_status = local.TIME_STAMP_TOKEN_NO_DATA
                     verifyResult.validation_user = userid
                     verifyResult.validation_date = datetime.datetime.now()
                     # ファイルが削除されていて検証結果があり場合、検証結果テーブルを更新する。
                     ret = local.TIME_STAMP_TOKEN_NO_DATA
                     verify_result_title = 'NOT TIMESTAMP_TOKEN'
            
            if ret == 0:
                timestamptoken_file = guid + '.tsr'
                timestamptoken_file_path  = os.path.join(tmp_dir, timestamptoken_file) 
                try: 
                    with open(timestamptoken_file_path , "wb") as fout:        
                        fout.write(verifyResult.timestamp_token)
                        
                except Exception as err:
                    raise err

                # 取得したタイムスタンプトークンと鍵情報から検証を行う。
                cmd = [local.OPENSSL_MAIN_CMD, local.OPENSSL_OPTION_TS, local.OPENSSL_OPTION_VERIFY,
                       local.OPENSSL_OPTION_DATA, os.path.join(tmp_dir, file_name), local.OPENSSL_OPTION_IN, timestamptoken_file_path, 
                       local.OPENSSL_OPTION_CAFILE, os.path.join(local.KEY_SAVE_PATH, local.VERIFY_ROOT_CERTIFICATE)]
                prc = subprocess.Popen(cmd, shell=False, 
                                       stdin=subprocess.PIPE, 
                                       stderr=subprocess.PIPE, 
                                       stdout=subprocess.PIPE)
                stdout_data, stderr_data = prc.communicate()
                ret = local.TIME_STAMP_TOKEN_UNCHECKED
                if stdout_data.__str__().find(local.OPENSSL_VERIFY_RESULT_OK) > -1:
                   ret = local.TIME_STAMP_TOKEN_CHECK_SUCCESS
                   verify_result_title = 'OK'
                else:
                   ret = local.TIME_STAMP_TOKEN_CHECK_NG
                   verify_result_title = 'NG'
                verifyResult.inspection_result_status = ret
                verifyResult.validation_user = userid
                verifyResult.validation_date = datetime.datetime.now()
                os.remove(timestamptoken_file_path)

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
                filename = self.get_filenameStruct(baseFileNode, "")
            else:
                filename = baseFileNode._path
            filepath = baseFileNode.provider + filename
            abstractNode = self.get_abstractNode(baseFileNode.node_id)
        else:
            filepath = provider + path
            abstractNode = self.get_abstractNode(Guid.objects.get(_id=project_id).object_id)
       
        ## RDM Logger ##
#        import sys
        rdmlogger = RdmLogger(rdmlog, {})
        rdmlogger.info("RDM Project", RDMINFO="TimeStampVerify", result_status=ret, user=guid, project=abstractNode.title, file_path=filepath)
        return {'verify_result': ret, 'verify_result_title': verify_result_title, 
                'operator_user': operator_user, 'operator_date': operator_date, 
                'filepath': filepath}

