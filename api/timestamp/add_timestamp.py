# -*- coding: utf-8 -*-
import requests
import datetime
from osf.models import RdmFileTimestamptokenVerifyResult, RdmUserKey, Guid
from urllib3.util.retry import Retry
import subprocess
from api.base import settings as api_settings
from api.timestamp.timestamptoken_verify import TimeStampTokenVerifyCheck
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)

class AddTimestamp:

    #1 get user key info
    def get_userkey(self, user_id):
        userKey = RdmUserKey.objects.get(guid=user_id, key_kind=api_settings.PUBLIC_KEY_VALUE)
        return userKey.key_name

    #2 create  tsq(timestamp request) from file, and keyinfo
    def get_timestamp_request(self, file_name):
        cmd = [api_settings.OPENSSL_MAIN_CMD, api_settings.OPENSSL_OPTION_TS, api_settings.OPENSSL_OPTION_QUERY, api_settings.OPENSSL_OPTION_DATA,
               file_name, api_settings.OPENSSL_OPTION_CERT, api_settings.OPENSSL_OPTION_SHA512]
        process = subprocess.Popen(cmd, shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        stdout_data, stderr_data = process.communicate()
        return stdout_data

    #3 send tsq to TSA, and recieve tsr(timestamp token)
    def get_timestamp_response(self, file_name, ts_request_file, key_file):
        res_content = None
        try:
            retries = Retry(total=api_settings.REQUEST_TIME_OUT,
                            backoff_factor=1, status_forcelist=api_settings.ERROR_HTTP_STATUS)
            session = requests.Session()
            session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

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

    #4 get timestamp verified result
    def get_data(self, file_id, project_id, provider, path):
        try:
            res = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_id)

        except ObjectDoesNotExist:
            #logger.exception(ex)
            res = None

        return res

    #5 register verify result in db
    def timestamptoken_register(self, file_id, project_id, provider, path,
                                key_file, tsa_response, user_id, verify_data):

        try:
            # data not registered yet
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

            # registered data:
            else:
                verify_data.key_file_name = key_file
                verify_data.timestamp_token = tsa_response
                verify_data.update_user = user_id
                verify_data.update_date = datetime.datetime.now()

            verify_data.save()

        except Exception as ex:
            logger.exception(ex)

        return

    #6 main
    def add_timestamp(self, guid, file_id, project_id, provider, path, file_name, tmp_dir):

        # get user_id from guid
        user_id = Guid.objects.get(_id=guid).object_id

        # get user key info
        key_file_name = self.get_userkey(user_id)

        # create tsq
        tsa_request = self.get_timestamp_request(file_name)

        # get tsr
        tsa_response = self.get_timestamp_response(file_name, tsa_request, key_file_name)

        # check that data exists
        verify_data = self.get_data(file_id, project_id, provider, path)

        # register in db
        self.timestamptoken_register(file_id, project_id, provider, path,
                                     key_file_name, tsa_response, user_id, verify_data)

        # tsr verification request call
        return TimeStampTokenVerifyCheck().timestamp_check(guid, file_id,
                                                           project_id, provider, path, file_name, tmp_dir)
