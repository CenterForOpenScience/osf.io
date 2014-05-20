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


def get_file(study, filename, released=False):
    return study.get_file(filename, released)


def get_file_by_id(study, file_id, released=False):
    return study.get_file_by_id(file_id, released)


def get_files(study, released=False):
    return study.get_files(released)


def release_study(study):
    return study.release()


def get_studies(dataverse):
    studies = dataverse.get_studies()
    acessible_studies = [s for s in studies if s.get_state() != 'DEACCESSIONED']
    return acessible_studies


def get_study(dataverse, hdl):
    study = dataverse.get_study_by_hdl(hdl)
    return study if study.get_state() != 'DEACCESSIONED' else None