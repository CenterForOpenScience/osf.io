from enum import IntEnum


class BoaErrorCode(IntEnum):
    """Define 5 types of failures and errors during Boa submit.
    """

    UNKNOWN = 0  # Unexpected error from WB and/or Boa
    QUERY_ERROR = 1  # Fail to compile or execute the Boa query
    UPLOAD_ERROR = 2  # Fail to upload the result output file to OSF
    OUTPUT_ERROR = 3  # Fail to retrieve the output after Boa job has finished
    AUTHN_ERROR = 4  # Fail to authenticate with Boa
