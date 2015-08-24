from modularodm import Q
from website import mails
from website.app import init_app
from framework.auth.core import User
from website.project.model import Node

GBs = (1024 ** 3)

NODE_CUT_OFF = 2 * GBs
USER_CUT_OFF = 2 * GBs
COLLAB_CUT_OFF = 2 * GBs


def find_problem_users():
    ret = []
    for user in User.find(Q('is_registered', 'eq', True) & Q('is_claimed', 'eq', True)):
        addon = user.get_addon('osfstorage')

        usage = addon.calculate_storage_usage(deleted=True)
        if usage > USER_CUT_OFF:
            ret.append('User {!r} has exceeded the user cut off of {} with a usage of {} (including deleted)'.format(user, USER_CUT_OFF, usage))
            continue

        usage = addon.calculate_collaborative_usage(deleted=True)
        if usage > COLLAB_CUT_OFF:
            ret.append('User {!r} has exceeded the collaborative cut off of {} with a usage of {} (including deleted)'.format(user, COLLAB_CUT_OFF, usage))
            continue

        usage = addon.calculate_collaborative_usage()
        if usage > COLLAB_CUT_OFF:
            ret.append('User {!r} has exceeded the collaborative cut off of {} with a usage of {} (excluding deleted)'.format(user, COLLAB_CUT_OFF, usage))
            continue

    return ret

def find_problem_nodes():
    ret = []
    for node in Node.find():
        if node.parent_id:
            continue  # Dont bother with children

        addon = node.get_addon('osfstorage')

        usage = addon.calculate_storage_usage(deleted=True)
        if usage > NODE_CUT_OFF:
            ret.append('Project {!r} has exceeded the project cut off of {} with a usage of {} (including deleted)'.format(node, NODE_CUT_OFF, usage))
            continue

        usage = addon.calculate_storage_usage()
        if usage > NODE_CUT_OFF:
            ret.append('Project {!r} has exceeded the project cut off of {} with a usage of {} (excluding deleted)'.format(node, NODE_CUT_OFF, usage))
            continue

    return ret

def main():
    init_app(set_backends=True, routes=False)
    body = '\n'.join(find_problem_nodes() + find_problem_users())
    if body:
        mails.send_mail('support@osf.io', mails.EMPTY, body=body)
    else:
        print('Nothing to do')


if __name__ == '__main__':
    main()
