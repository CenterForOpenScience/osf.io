from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.settings import TEST_CERT, HOST


def connect(username, password, host=HOST):
    connection = DvnConnection(
        username=username,
        password=password,
        host=host,
        cert=TEST_CERT,
    )
    return connection if connection.connected else None


def delete_file(study, file):
    study.delete_file(file)