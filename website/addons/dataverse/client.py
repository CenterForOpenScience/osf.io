from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.settings import TEST_CERT, HOST


def connect(username, password, host=HOST):
    connection = DvnConnection(
        username=username,
        password=password,
        host=host,
        cert=TEST_CERT,
        disable_ssl_certificate_validation=True,
    )
    return connection if connection.connected else None


def delete_file(file):
    study = file.hostStudy
    study.delete_file(file)


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
    if dataverse is None:
        return []
    studies = dataverse.get_studies()
    accessible_studies = [s for s in studies if s.get_state() != 'DEACCESSIONED']
    return accessible_studies


def get_study(dataverse, hdl):
    if dataverse is None:
        return
    study = dataverse.get_study_by_hdl(hdl)
    return study if study and study.get_state() != 'DEACCESSIONED' else None


def get_dataverses(connection):
    if connection is None:
        return []
    dataverses = connection.get_dataverses()
    released_dataverses = [d for d in dataverses if d.is_released]
    return released_dataverses


def get_dataverse(connection, alias):
    if connection is None:
        return
    dataverse = connection.get_dataverse(alias)
    return dataverse if dataverse and dataverse.is_released else None

