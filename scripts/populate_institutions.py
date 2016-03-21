#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Institution fixtures."""
import sys
import urllib

from website import settings
from website.app import init_app
from website.models import Institution, Node
from framework.transactions.context import TokuTransaction

ENVS = ['prod', 'nonprod']
SHIBBOLETH_SP = '{}/Shibboleth.sso/Login?entityID={{}}'.format(settings.CAS_SERVER_URL)

def update_or_create(inst_data):
    inst = Institution.load(inst_data['_id'])
    if inst:
        for key, val in inst_data.iteritems():
            setattr(inst.node, inst.attribute_map[key], val)
        changed_fields = inst.node.save()
        if changed_fields:
            print('Updated {}: {}'.format(inst.name, changed_fields))
        return inst, False
    else:
        inst = Institution(None)
        inst_data = {inst.attribute_map[k]: v for k, v in inst_data.iteritems()}
        new_inst = Node(**inst_data)
        new_inst.save()
        print('Added new institution: {}'.format(new_inst.institution_id))
        return new_inst, True


def main(env):
    INSTITUTIONS = [
        {
            'name': 'University of Notre Dame',
            '_id': 'nd',
            'logo_name': 'notre-dame.jpg',
            'auth_url': SHIBBOLETH_SP.format(
                urllib.quote('https://login.nd.edu/idp/shibboleth', safe='~()*!.\'') if env == 'prod' else urllib.quote('https://login-test.cc.nd.edu/idp/shibboleth', safe='~()*!.\'')
            ),
            'domains': [
                'osf.nd.edu' if env == 'prod' else 'staging-osf-nd.cos.io',
            ],
            'description': 'University of Notre Dame',
            'email_domains': [],
        },
        {
            'name': 'Center For Open Science',
            '_id': 'cos',
            'logo_name': 'cos.png',
            'auth_url': None,
            'domains': [
                'osf.cos.io' if env == 'prod' else 'staging-osf.cos.io',
            ],
            'description': 'Center for Open Science',
            'email_domains': [
                'cos.io',
            ],
            'banner_name': 'cos-banner.png'
        },
        {
            'name': 'University of Southern California',
            '_id': 'usc',
            'logo_name': 'usc-shield.jpg',
            'auth_url': SHIBBOLETH_SP.format(
                urllib.quote('https://shibboleth.usc.edu/shibboleth-idp', safe='~()*!.\'') if env == 'prod' else urllib.quote('https://shibboleth-test.usc.edu/shibboleth-idp', safe='~()*!.\'')
            ),
            'domains': [
                'osf.nd.edu' if env == 'prod' else 'staging-osf-usc.cos.io',
            ],
            'description': 'University of Southern California',
            'email_domains': [],
            'banner_name': 'usc-banner.png'
        },

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
