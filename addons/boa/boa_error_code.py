from enum import IntEnum


class BoaErrorCode(IntEnum):
    """Define 4 types of failures and errors during Boa submit.
    """

    UNKNOWN = 0  # Unexpected error
    QUERY_ERROR = 1  # Compile or execution error
    UPLOAD_ERROR = 2  # Fail to upload the result output file to OSF
    AUTHN_ERROR = 3  # Fail to log in to Boa
