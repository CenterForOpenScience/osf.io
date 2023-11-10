from enum import IntEnum


class BoaErrorCode(IntEnum):
    """Define 8 types of failures and errors (0~7) and 1 type for no error (-1) during Boa submit.
    """

    NO_ERROR = -1               # No error
    UNKNOWN = 0                 # Unexpected error from WB and/or Boa
    AUTHN_ERROR = 1             # Fail to authenticate with Boa
    QUERY_ERROR = 2             # Fail to compile or execute the Boa query
    UPLOAD_ERROR_CONFLICT = 3   # Fail to upload the output to OSF because file already exists
    UPLOAD_ERROR_OTHER = 4      # Fail to upload the output to OSF due to reasons other than ``UPLOAD_ERROR_CONFLICT``
    OUTPUT_ERROR = 5            # Fail to retrieve the output after Boa job has finished
    FILE_TOO_LARGE_ERROR = 6    # Fail to submit to Boa due to query file too large
    JOB_TIME_OUT_ERROR = 7      # Fail to finish Boa job due to time out
