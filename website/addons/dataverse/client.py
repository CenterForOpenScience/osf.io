from website.addons.dataverse.dvn.study import Study
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


def delete_file(file):
    Study.delete_file(file.hostStudy, file)


def upload_file(study, filename, content):
    study.add_file_obj(filename, content)

def get_file(study, filename):
    return study.get_file(filename)