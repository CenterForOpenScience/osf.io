from website.project.views.email import Conference
from website.models import User
from modularodm import Q
from modularodm.exceptions import ModularOdmException
from website.app import init_app
import sys
import argparse

def main():
    init_app(set_backends=True, routes=False)
    args = parse_args()
    add_conference(
        endpoint=args.endpoint,
        name=args.name,
        active=args.active,
        info_url=args.info_url,
        logo_url=args.logo_url,
        admins=args.admins,
        public_projects=args.public_projects
    )

def add_conference(endpoint, name, active, info_url=None,
               logo_url=None, admins=None, public_projects=None):
    try:
        admin_users = [
            User.find_one(Q('username', 'iexact', admin))
            for admin in admins
        ]
    except ModularOdmException:
        raise RuntimeError("Admin must be a current registered user on the OSF.")

    conf = Conference(
        endpoint=endpoint,
        name=name,
        active=active,
        info_url=info_url,
        logo_url=logo_url,
        admins=admin_users
    )
    try:
        conf.save()
    except ModularOdmException:
        raise RuntimeError("Conference already exists.")

def parse_args():
    parser = argparse.ArgumentParser(description='Create new conference.')
    parser.add_argument('-e', '--endpoint', dest='endpoint', required=True)
    parser.add_argument('--n', '--name', dest='name', required=True)
    parser.add_argument('--active', dest='active', type=bool, default=False)
    parser.add_argument('--i_url', '--info_url', dest='info_url')
    parser.add_argument('--l_url', '--logo_url', dest='logo_url')
    parser.add_argument('--admins', dest='admins', nargs='+')
    parser.add_argument('--public', '--public_projects', dest='public_projects', type=bool, default=None)
    return parser.parse_args()


if __name__ == '__main__':
    main()

