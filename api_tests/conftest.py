import logging
import pytest

from tests.json_api_test_app import JSONAPITestApp

# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [

]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

@pytest.fixture()
def app():
    return JSONAPITestApp()
