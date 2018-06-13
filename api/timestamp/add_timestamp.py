# -*- coding: utf-8 -*-
import requests
import datetime
#from modularodm import Q
from osf.models import RdmFileTimestamptokenVerifyResult, RdmUserKey, Guid
from urllib3.util.retry import Retry
import subprocess
#import os
#from StringIO import StringIO
from api.base import settings as api_settings
from api.timestamp.timestamptoken_verify import TimeStampTokenVerifyCheck

import logging

logger = logging.getLogger(__name__)

class AddTimestamp:

    #①鍵情報テーブルから操作ユーザに紐づく鍵情報を取得する
    def get_userkey(self, user_id):
        userKey = RdmUserKey.objects.get(guid=user_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        return userKey.key_name

    #②ファイル情報 + 鍵情報をハッシュ化したタイムスタンプリクエスト（tsq）を生成する
    def get_timestamp_request(self, file_name):
        cmd = [api_settings.OPENSSL_MAIN_CMD, api_settings.OPENSSL_OPTION_TS, api_settings.OPENSSL_OPTION_QUERY, api_settings.OPENSSL_OPTION_DATA,
               file_name, api_settings.OPENSSL_OPTION_CERT, api_settings.OPENSSL_OPTION_SHA512]
        process = subprocess.Popen(cmd, shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        stdout_data, stderr_data = process.communicate()
        return stdout_data

    #③tsqをTSAに送信してタイムスタンプトークン（tsr）を受け取る
    def get_timestamp_response(self, file_name, ts_request_file, key_file):
        res_content = None
        try:
            retries = Retry(total=api_settings.REQUEST_TIME_OUT,
                            backoff_factor=1, status_forcelist=api_settings.ERROR_HTTP_STATUS)
            session = requests.Session()
            session.mount("http://", requests.adapters.HTTPAdapter(max_retries=retries))
            session.mount("https://", requests.adapters.HTTPAdapter(max_retries=retries))

            res = requests.post(api_settings.TIME_STAMP_AUTHORITY_URL,
                                headers=api_settings.REQUEST_HEADER, data=ts_request_file, stream=True)
            res_content = res.content
            res.close()
        except Exception as ex:
            logger.exception(ex)
            import traceback
            traceback.print_exc()
            res_content = None

        return res_content

    #④データの取得
    def get_data(self, file_id, project_id, provider, path):
        try:
            res = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_id)

        except Exception as ex:
            logger.exception(ex)
            res = None

        return res

    #⑤ファイルタイムスタンプトークン情報テーブルに登録。
    def timestamptoken_register(self, file_id, project_id, provider, path,
                                key_file, tsa_response, user_id, verify_data):

        try:
            # データが登録されていない場合
            if not verify_data:
                verify_data = RdmFileTimestamptokenVerifyResult()
                verify_data.key_file_name = key_file
                verify_data.file_id = file_id
                verify_data.project_id = project_id
                verify_data.provider = provider
                verify_data.path = path
                verify_data.timestamp_token = tsa_response
                verify_data.inspection_result_status = api_settings.TIME_STAMP_TOKEN_UNCHECKED
                verify_data.create_user = user_id
                verify_data.create_date = datetime.datetime.now()

            # データがすでに登録されている場合
            else:
                verify_data.key_file_name = key_file
                verify_data.timestamp_token = tsa_response
                verify_data.update_user = user_id
                verify_data.update_date = datetime.datetime.now()

            verify_data.save()

        except Exception as ex:
            logger.exception(ex)
#            res = None

        return

    #⑥メイン処理
    def add_timestamp(self, guid, file_id, project_id, provider, path, file_name, tmp_dir):

        #        logger.info('add_timestamp start guid:{guid} project_id:{project_id} provider:{provider} path:{path} file_name:{file_name} file_id:{file_id}'.format(guid=guid,project_id=project_id,provider=provider,path=path,file_name=file_name, file_id=file_id))

        # guid から user_idを取得する
        #user_id = Guid.find_one(Q('_id', 'eq', guid)).object_id
        user_id = Guid.objects.get(_id=guid).object_id

        # ユーザ鍵情報を取得する。
        key_file_name = self.get_userkey(user_id)

        # タイムスタンプリクエスト生成
        tsa_request = self.get_timestamp_request(file_name)

        # タイムスタンプトークン取得
        tsa_response = self.get_timestamp_response(file_name, tsa_request, key_file_name)

        # 検証データ存在チェック
        verify_data = self.get_data(file_id, project_id, provider, path)

        # 検証結果テーブルに登録する。
        self.timestamptoken_register(file_id, project_id, provider, path,
                                     key_file_name, tsa_response, user_id, verify_data)

        # （共通処理）タイムスタンプ検証処理の呼び出し
        return TimeStampTokenVerifyCheck().timestamp_check(guid, file_id,
                                                           project_id, provider, path, file_name, tmp_dir)
