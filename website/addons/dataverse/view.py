from .model import UserSettings, NodeSettings

# User settings

def get_user_settings(user, label):
    '''Look up user settings by user and label. Return first
    matching settings or None.

    :param user:
    :param label:
    :return: UserSettings or None

    '''
    user_settings = [
        us
        for us in user.usersettings__dataverse
        if us.label == label
    ]
    if user_settings:
        return user_settings[0]

def add_user_settings(user, username, password, label):
    '''Create user settings and attach to user.

    :param user:
    :param username:
    :param password:
    :param label:

    '''
    if get_user_settings(user, label):
        return
    user_settings = UserSettings(
        user=user,
        username=username,
        password=password,
        label=label,
    )
    user_settings.save()

def remove_user_settings(user, label):
    '''Delete user settings by label if found.

    :param user:
    :param label:
    '''
    user_settings = get_user_settings(user, label)
    if user_settings:
        UserSettings.remove_one(user_settings)
        return True
    return False

# Node settings

def get_node_settings(node, dataverse, study):
    '''

    :param node:
    :param dataverse:
    :param study:
    :return: NodeSettings or None
    '''
    node_settings = [
        ns
        for ns in node.nodesettings__dataverse
        if ns.dataverse == dataverse
        and ns.study == study
    ]
    if node_settings:
        return node_settings[0]

def add_node_settings(node, user_settings, dataverse, study):
    '''

    :param node:
    :param user_settings:
    :param dataverse:
    :param study:

    '''
    if get_node_settings(dataverse, study):
        return
    node_settings = NodeSettings(
        node=node,
        user_settings=[user_settings],
        dataverse=dataverse,
        study=study,
    )
    node_settings.save()

def get_dataverse(user_settings, node_settings):
    pass

def get_study(user_settings, node_settings):
    pass

def create_dataverse(user_settings, node_settings):
    pass

def create_study(user_settings, node_settings):
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
        NodeSettings.remove_one(node_settings)
        return True
    return False

# Files

def list_files(user_settings, node_settings):
    pass

def add_file(user_settings, node_settings, file):
    pass

def update_file(user_settings, node_settings, file):
    pass

def remove_file(user_settings, node_settings, dataverse_file):
    pass

def download_file(user_settings, node_settings, dataverse_file):
    pass

# Collaboration

def create_dataverse_user():
    pass

def add_user_as_admin():
    pass

def remove_user_as_admin():
    pass