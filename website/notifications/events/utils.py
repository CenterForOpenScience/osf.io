
from website.notifications.emails import compile_subscriptions
from website.notifications import utils, constants


def get_file_subs_from_folder(addon, user, kind, path, name):
    folder = dict(kind=kind, path=path, name=name)
    file_tree = addon._get_file_tree(filenode=folder, user=user, version='latest-published')
    files = []
    list_of_files(file_tree, files)
    return files


def list_of_files(file_object, files):
    if file_object['kind'] == 'file':
        files.append(file_object['path'])
    else:
        for child in file_object['children']:
            list_of_files(child, files)


def get_file_guid(node, provider, path):
    path = path if path.startswith('/') else '/' + path
    addon = node.get_addon(provider)
    guid, created = addon.find_or_create_file_guid(path)
    return guid


def compile_user_lists(files, user, source_node, node):
    """
    takes multiple files and compiles them
    :param files: List of WaterButler paths
    :param user: User who initiated action/event
    :param source_node: Node instance from
    :param node: Node instance to
    :return: move, warn, and remove dicts
    """
    move = {key: [] for key in constants.NOTIFICATION_TYPES}
    warn = {key: [] for key in constants.NOTIFICATION_TYPES}
    remove = {key: [] for key in constants.NOTIFICATION_TYPES}
    if len(files) == 0:
        move, warn, remove = \
            categorize_users(user, 'file_updated', source_node, 'file_updated', node)
    for file_path in files:
        path = file_path.strip('/')
        t_move, t_warn, t_remove = \
            categorize_users(user, path + '_file_updated', source_node,
                             path + '_file_updated', node)
        for notification in constants.NOTIFICATION_TYPES:
            move[notification] = list(set(move[notification]).union(set(t_move[notification])))
            warn[notification] = list(set(warn[notification]).union(set(t_warn[notification])))
            remove[notification] = list(set(remove[notification]).union(set(t_remove[notification])))
    return move, warn, remove


def categorize_users(user, source_event, source_node, event, node):
    """
    Puts users in one of three bins: Those that are moved, those that need warned, those that are removed.
    Calls move_subscription in order to move the sub and get users w/o permissions
    :param user: User instance who started the event
    :param source_event: <guid>_event_name
    :param source_node: node from where the event happened
    :param event: new guid event name
    :param node: node where event ends up
    :return: Moved, to be warned, and removed users.
    """
    remove = utils.users_to_remove(source_event, source_node, node)
    source_node_subs = compile_subscriptions(source_node, '_'.join(source_event.split('_')[-2:]))
    new_subs = compile_subscriptions(node, '_'.join(source_event.split('_')[-2:]), event)
    warn = {key: [] for key in constants.NOTIFICATION_TYPES}
    move = {key: [] for key in constants.NOTIFICATION_TYPES}
    for notifications in constants.NOTIFICATION_TYPES:
        if notifications == 'none':
            continue
        move[notifications] = list(set(source_node_subs[notifications]).union(set(new_subs[notifications])))
        warn[notifications] = list(set(source_node_subs[notifications]).difference(set(new_subs[notifications])))
        subbed, removed = utils.separate_users(node, warn[notifications])
        warn[notifications] = subbed
        remove[notifications].extend(removed)
        remove[notifications] = list(set(remove[notifications]))
    # Remove duplicates in different types
    for notifications in constants.NOTIFICATION_TYPES:
        if notifications == 'none':
            continue
        for nt in constants.NOTIFICATION_TYPES:
            if nt == 'none':
                continue
            if nt != notifications:
                warn[notifications] = list(set(warn[notifications]).difference(set(new_subs[nt])))
                move[notifications] = list(set(move[notifications]).difference(set(new_subs[nt])))
    # Remove final duplicates in all types
    for notifications in constants.NOTIFICATION_TYPES:
        if notifications == 'none':
            continue
        for nt in constants.NOTIFICATION_TYPES:
            if nt == 'none':
                continue
            move[notifications] = list(set(move[notifications]).difference(set(warn[nt])))
            move[notifications] = list(set(move[notifications]).difference(set(remove[nt])))
        # Remove the user who started this whole thing.
        user_id = user._id
        if user_id in warn[notifications]:
            warn[notifications].remove(user_id)
        if user_id in move[notifications]:
            move[notifications].remove(user_id)
        if user_id in remove[notifications]:
            remove[notifications].remove(user_id)

    return move, warn, remove
