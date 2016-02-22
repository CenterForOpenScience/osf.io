#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Institution fixtures."""
import sys

from website.app import init_app
from website.models import Institution
from framework.transactions.context import TokuTransaction

ENVS = ['prod', 'nonprod']
SHIBBOLETH_SP = 'https://staging-accounts.osf.io/Shibboleth.sso/Login?entityID={}'

def update_or_create(inst_data):
    inst = Institution.load(inst_data['_id'])
    if inst:
        for key, val in inst_data.iteritems():
            inst.key = val
        changed_fields = inst.save()
        if changed_fields:
            print('Updated {}: {}'.format(inst.name, changed_fields))
        return inst, False
    else:
        new_inst = Institution(**inst_data)
        new_inst.save()
        print('Added new institution: {}'.format(new_inst._id))
        return new_inst, True


def main(env):
    INSTITUTIONS = [
        {
            'name': 'Virginia Tech',
            '_id': 'VT',
            'logo_name': 'virginia-tech.jpg',
            'auth_url': SHIBBOLETH_SP.format(
                'https://shib-pprd.middleware.vt.edu'
            )
        },
        {
            'name': 'Notre Dame',
            '_id': 'ND',
            'logo_name': 'notre-dame.jpg',
            'auth_url': SHIBBOLETH_SP.format(
                'https://login.nd.edu/idp/shibboleth' if env == 'prod' else 'https://login-test.cc.nd.edu/idp/shibboleth'
            )
        }
    ]

    init_app(routes=False)
    for inst_data in INSTITUTIONS:
        with TokuTransaction():
            new_inst, inst_created = update_or_create(inst_data)


if __name__ == '__main__':
    env = str(sys.argv[1]).lower() if len(sys.argv) >= 1 else None
    if env not in ENVS:
        print('An environment must be specified : {}', ENVS)
        sys.exit(1)
    main(env)
