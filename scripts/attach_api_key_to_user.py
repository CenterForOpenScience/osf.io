import argparse
from website.project.model import ApiKey
from framework.auth.core import User
from modularodm.query.querydialect import DefaultQueryDialect as Q
from website.app import init_app


app = init_app('website.settings', set_backends=True, routes=True)


def parse_args():
    parser = argparse.ArgumentParser(description='Create fake data.')
    parser.add_argument('-u', '--user', dest='user', required=True)
    return parser.parse_args()


def gen_api_key():
    api_key = ApiKey()
    api_key.save()
    return api_key


def get_user(args):
    username = args.user
    user = User.find(Q('username', 'eq', username))[0]
    return user


def attach_api_key(user, api_key):
    user.api_keys.append(api_key)
    return user.save()


def main():
    args = parse_args()
    api_key = gen_api_key()
    user = get_user(args)
    print('\n\nApi key: \n\t{}\n\n'.format(api_key._id))
    return attach_api_key(user, api_key)

if __name__ == '__main__':
    main()
