# todo move logic into models

import re

from .model import DataverseUserSettings, DataverseNodeSettings
from website.models import User, Node
from framework import request

from BeautifulSoup import BeautifulSoup as Soup
from sword2.exceptions import HTTPResponseError

# todo make swordpoc installable
# todo: move to_json methods into swordpoc
from dvnclient.connection import DvnConnection
from dvnclient.dataverse import Dataverse
from dvnclient.study import Study
from dvnclient.file import DvnFile

def dataverse_to_json(self):
    return {
        'title' : self.collection.title,
        'col-iri' : self.collection.href,
    }
Dataverse.to_json = dataverse_to_json

def study_to_json(self):
    return {
        'title' : self.editUri.split('/')[-1],
    }
Study.to_json = study_to_json

def dvn_file_to_json(self):
    return {
        'fname' : self.editMediaUri.split('/')[-1],
    }
DvnFile.to_json = dvn_file_to_json

DV_SSL = '/Users/jmcarp/Desktop/dvn-4.hmdc.harvard.edu'

# Todo: move elsewhere
# Utility functions
def parse_sword_error(error):
    return Soup(error.content)\
        .find('atom:summary')\
        .text

def credentials_valid(user_settings):
    connection = get_dataverse_connection(user_settings=user_settings)
    return not connection.swordConnection.raise_except

# User settings

def get_user_settings(**kwargs):
    user = kwargs.get('user') or User.load(request.form['user_id'])
    label = kwargs.get('label') or request.form['label']
    user_settings = [
        us
        for us in user.dataverseusersettings__dataverse
        if us.label == label
    ]
    if user_settings:
        return user_settings[0]

def add_user_settings(**kwargs):
    user = kwargs.get('user') or User.load(request.form['user_id'])
    label = kwargs.get('label') or request.form['label']
    if get_user_settings(user=user, label=label):
        return {
            'status' : 'failure',
            'message' : 'Credentials with label {} for user {} already exist.'.format(
                label, user._primary_key
            ),
        }
    user_settings = DataverseUserSettings(
        user=user,
        network_title=request.form['network_title'],
        network_uri=request.form['network_uri'],
        username=request.form['username'],
        password=request.form['password'],
        label=request.form['label'],
    )
    valid = credentials_valid(user_settings)
    if not valid:
        return {
            'status' : 'failure',
            'message' : 'Invalid credentials',
        }
    user_settings.save()
    return {
        'status' : 'success',
        'user_settings_id' : user_settings._primary_key,
    }

def remove_user_settings(**kwargs):
    user = kwargs.get('user') or User.load(request.form['user_id'])
    label = kwargs.get('label') or request.form['label']
    user_settings = get_user_settings(user=user, label=label)
    if user_settings:
        DataverseUserSettings.remove_one(user_settings)
        return {
            'status' : 'success'
        }
    return {
        'status' : 'failure',
        'message' : 'No credentials with label {} for user {}.'.format(
            label, user._primary_key
        ),
    }

def list_dataverses(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    connection = get_dataverse_connection(user_settings=user_settings)
    return connection.get_dataverses()

# Node settings

def get_node_settings(**kwargs):
    node = kwargs.get('node') or Node.load(request.form['node_id'])
    dataverse_alias = kwargs.get('dataverse_alias') or request.form['dataverse_alias']
    study_global_id = kwargs.get('study_global_id') or request.form['study_global_id']
    node_settings = [
        ns
        for ns in node.dataversenodesettings__dataverse
        if ns.dataverse_alias == dataverse_alias
        and ns.study_global_id == study_global_id
    ]
    if node_settings:
        return node_settings[0]

def add_node_settings(**kwargs):
    node = Node.load(request.form['node_id'])
    user_settings = DataverseUserSettings.load(request.form['user_settings_id'])
    # if get_node_settings(dataverse, study):
    #     return
    node_settings = DataverseNodeSettings(
        node=node,
        user_settings=[user_settings],
        network_uri=user_settings.network_uri,
        dataverse_alias=request.form['dataverse_alias'],
        study_global_id=request.form['study_global_id'],
    )
    # study = get_study(user_settings, node_settings)
    # if study is None:
    #     create_study(user_settings, node_settings)
    node_settings.save()
    return {
        'status' : 'success',
        'node_settings_id' : user_settings._primary_key,
    }

def get_dataverse_connection(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    return DvnConnection(
        user_settings.username,
        user_settings.password,
        user_settings.network_uri,
        DV_SSL,
    )

def get_dataverse(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    dataverse_title = kwargs.get('dataverse_title') or \
        request.form['dataverse_title']
    dataverses = [
        dv
        for dv in list_dataverses(user_settings=user_settings)
        if dv.collection.title == dataverse_title
    ]
    if dataverses:
        return dataverses[0]

def list_studies(**kwargs):
    user_settings = kwargs.get(
        'user_settings',
        DataverseUserSettings.load(request.form['user_settings_id'])
    )
    dataverse = get_dataverse(
        user_settings=user_settings,
        dataverse_title='CoS Dataverse'
    )
    return dataverse.get_studies()

def get_study(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])
    dataverse = get_dataverse(
        user_settings=user_settings,
        dataverse_title=node_settings.dataverse_alias
    )
    if dataverse:
        study = dataverse.get_study_by_hdl(node_settings.study_global_id)
        return study

def create_dataverse():
    raise NotImplementedError

def create_study(**kwargs):

    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])

    study = Study.CreateStudyFromDict({
        'title' : user_settings.study_title,
        'author' : '',
        'abstract' : '',
    })
    dataverse = get_dataverse(
        user_settings=user_settings,
        node_settings=node_settings
    )

    try:
        dataverse.add_study(study)
    except Exception as error:
        return {
            'status' : 'failure',
            'message' : parse_sword_error(error),
        }

def get_service_document(user_settings, node_settings):
    pass

def add_user_settings_to_node_settings(user_settings, node_settings):

    node_settings.user_settings.append(user_settings)
    node_settings.save()

def remove_user_settings_from_node_settings(user_settings, node_settings):

    node_settings.user_settings.remove(user_settings)
    node_settings.save()

def remove_node_settings(node, dataverse, study):
    '''

    :param node:
    :param dataverse:
    :param study:
    :return: bool -- status
    '''
    node_settings = get_node_settings(node, dataverse, study)
    if node_settings:
        DataverseNodeSettings.remove_one(node_settings)
        return True
    return False

# Files

def list_files(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])
    study = get_study(
        user_settings=user_settings,
        node_settings=node_settings,
    )
    return study.get_files()

def add_file(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])
    study = get_study(
        user_settings=user_settings,
        node_settings=node_settings,
    )
    try:
        study.add_file(kwargs.get('fname') or request.form['fname'])
        return {
            'status' : 'success',
        }
    except HTTPResponseError as error:
        return {
            'status' : 'failure',
            'message' : parse_sword_error(error),
        }

def remove_file(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])
    fname = kwargs.get('fname') or request.form['fname']
    files = list_files(
        user_settings=user_settings,
        node_settings=node_settings,
    )
    files = [
        f
        for f in files
        if f.name == fname
    ]
    if files:
        study = get_study(
            user_settings=user_settings,
            node_settings=node_settings,
        )
        study.delete_file(files[0])
    return {
        'status' : 'success',
    }

def update_file(**kwargs):
    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])
    fname = kwargs.get('fname') or request.form['fname']
    remove_file(**locals())
    add_file(**locals())

def get_download_url(**kwargs):

    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])
    fname = kwargs.get('fname') or request.form['fname']

    files = list_files(
        user_settings=user_settings,
        node_settings=node_settings,
    )
    files = [
        f
        for f in files
        if f.name == fname
    ]
    if files:
        fid = re.search('file\/(\d+)\/', files[0].editMediaUri, re.I).groups()[0]
        return '{base}/FileDownload/?fildId={fid}&xff=0&version={version}'.format(
            base=node_settings.network_uri,
            fid=fid,
            version=node_settings.version
        )

# Releases

def get_dataverse_released(**kwargs):

    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])

    dataverse = get_dataverse(
        user_settings=user_settings,
        node_settings=node_settings
    )

    try:
        return dataverse.is_released()
    except Exception as error:
        pass

def get_study_released(**kwargs):
    raise NotImplementedError

def release_dataverse(**kwargs):
    raise NotImplementedError

def release_study(**kwargs):

    user_settings = kwargs.get('user_settings') or \
        DataverseUserSettings.load(request.form['user_settings_id'])
    node_settings = kwargs.get('node_settings') or \
        DataverseNodeSettings.load(request.form['node_settings_id'])

    study = get_study(
        user_settings=user_settings,
        node_settings=node_settings
    )
    try:
        study.release()
    except Exception as error:
        pass

# Collaboration

def create_dataverse_user():
    raise NotImplementedError

def add_user_as_admin():
    raise NotImplementedError

def remove_user_as_admin():
    raise NotImplementedError