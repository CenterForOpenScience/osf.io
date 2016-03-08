#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Institution fixtures."""
import sys
import urllib

from website import settings
from website.app import init_app
from website.project.model import Institution, Node
from framework.transactions.context import TokuTransaction

ENVS = ['prod', 'nonprod']
SHIBBOLETH_SP = '{}/Shibboleth.sso/Login?entityID={{}}'.format(settings.CAS_SERVER_URL)

def update_or_create(inst_data):
    inst = Institution.load(inst_data['_id'])
    if inst:
        for key, val in inst_data.iteritems():
            setattr(inst.node, inst.attribute_map[key], val)
        inst.node.is_institution = True
        changed_fields = inst.node.save()
        if changed_fields:
            print('Updated {}: {}'.format(inst.name, changed_fields))
        return inst, False
    else:
        inst = Institution(None)
        inst_data = {inst.attribute_map[k]: v for k, v in inst_data.iteritems()}
        inst_data.update({'is_institution': True})
        new_inst = Node(**inst_data)
        new_inst.save()
        print('Added new institution: {}'.format(new_inst.institution_id))
        return new_inst, True


def main(env):
    INSTITUTIONS = [
        {
            'name': 'Virginia Tech',
            '_id': 'vt',
            'logo_name': 'virginia-tech.jpg',
            'auth_url': SHIBBOLETH_SP.format(
                urllib.quote('https://shib-pprd.middleware.vt.edu', safe='~()*!.\'')
            ),
            'domain': ['osf.vt.edu:5000'],
            'description': 'this is vt'
        },
        {
            'name': 'Notre Dame',
            '_id': 'nd',
            'logo_name': 'notre-dame.jpg',
            'auth_url': SHIBBOLETH_SP.format(
                urllib.quote('https://login.nd.edu/idp/shibboleth', safe='~()*!.\'') if env == 'prod' else urllib.quote('https://login-test.cc.nd.edu/idp/shibboleth', safe='~()*!.\'')
            ),
            'domain': ['osf.nd.edu:5000'],
            'description': 'this is nd'
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
