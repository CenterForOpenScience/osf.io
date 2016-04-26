#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Institution fixtures."""
import sys
import logging
import urllib

from modularodm import Q

from website import settings
from website.app import init_app
from website.models import Institution, Node
from website.search.search import update_institution, update_node
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENVS = ['prod', 'stage', 'stage2', 'test']
SHIBBOLETH_SP = '{}/Shibboleth.sso/Login?entityID={{}}'.format(settings.CAS_SERVER_URL)


def encode_uri_component(val):
    return urllib.quote(val, safe='~()*!.\'')


def update_or_create(inst_data):
    inst = Institution.load(inst_data['_id'])
    if inst:
        for key, val in inst_data.iteritems():
            setattr(inst.node, inst.attribute_map[key], val)
        changed_fields = inst.node.save()
        if changed_fields:
            print('Updated {}: {}'.format(inst.name, changed_fields))
        update_institution(inst)
        return inst, False
    else:
        inst = Institution(None)
        inst_data = {inst.attribute_map[k]: v for k, v in inst_data.iteritems()}
        new_inst = Node(**inst_data)
        new_inst.save()
        inst = Institution.load(new_inst.institution_id)
        print('Added new institution: {}'.format(new_inst.institution_id))
        update_institution(inst)
        return new_inst, True


def main(env):
    INSTITUTIONS = []

    if env == 'prod':
        INSTITUTIONS = [
            {
                '_id': 'cos',
                'name': 'Center For Open Science',
                'description': None,
                'banner_name': 'cos-banner.png',
                'logo_name': 'cos-shield.png',
                'auth_url': None,
                'domains': ['osf.cos.io'],
                'email_domains': ['cos.io'],
            },
            {
                '_id': 'nd',
                'name': 'University of Notre Dame',
                'description': None,
                'banner_name': 'nd-banner.png',
                'logo_name': 'nd-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('https://login.nd.edu/idp/shibboleth')),
                'domains': ['osf.nd.edu'],
                'email_domains': [],
            },
            {
                '_id': 'ucr',
                'name': 'University of California Riverside',
                'description': None,
                'banner_name': 'ucr-banner.png',
                'logo_name': 'ucr-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('urn:mace:incommon:ucr.edu')),
                'domains': ['osf.ucr.edu'],
                'email_domains': [],
            },
            {
                '_id': 'usc',
                'name': 'University of Southern California',
                'description': 'Projects must abide by <a href="http://policy.usc.edu/info-security/">USC\'s Information Security Policy</a>. Data stored for human subject research repositories must abide by <a href="http://policy.usc.edu/biorepositories/">USC\'s Biorepository Policy</a>. The OSF may not be used for storage of Personal Health Information that is subject to <a href="http://policy.usc.edu/hipaa/">HIPPA regulations</a>.',
                'banner_name': 'usc-banner.png',
                'logo_name': 'usc-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('urn:mace:incommon:usc.edu')),
                'domains': ['osf.usc.edu'],
                'email_domains': [],
            },
        ]
    if env == 'stage':
        INSTITUTIONS = [
            {
                '_id': 'cos',
                'name': 'Center For Open Science [Stage]',
                'description': 'Center for Open Science [Stage]',
                'banner_name': 'cos-banner.png',
                'logo_name': 'cos-shield.png',
                'auth_url': None,
                'domains': ['staging-osf.cos.io'],
                'email_domains': ['cos.io'],
            },
            {
                '_id': 'nd',
                'name': 'University of Notre Dame [Stage]',
                'description': 'University of Notre Dame [Stage]',
                'banner_name': 'nd-banner.png',
                'logo_name': 'nd-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('https://login-test.cc.nd.edu/idp/shibboleth')),
                'domains': ['staging-osf-nd.cos.io'],
                'email_domains': [],
            },
        ]
    if env == 'stage2':
        INSTITUTIONS = [
            {
                '_id': 'cos',
                'name': 'Center For Open Science [Stage2]',
                'description': 'Center for Open Science [Stage2]',
                'banner_name': 'cos-banner.png',
                'logo_name': 'cos-shield.png',
                'auth_url': None,
                'domains': ['staging2-osf.cos.io'],
                'email_domains': ['cos.io'],
            },
        ]
    elif env == 'test':
        INSTITUTIONS = [
            {
                '_id': 'cos',
                'name': 'Center For Open Science [Test]',
                'description': 'Center for Open Science [Test]',
                'banner_name': 'cos-banner.png',
                'logo_name': 'cos-shield.png',
                'auth_url': None,
                'domains': ['test-osf.cos.io'],
                'email_domains': ['cos.io'],
            },
            {
                '_id': 'nd',
                'name': 'University of Notre Dame [Test]',
                'description': 'University of Notre Dame [Test]',
                'banner_name': 'nd-banner.png',
                'logo_name': 'nd-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('https://login-test.cc.nd.edu/idp/shibboleth')),
                'domains': ['test-osf-nd.cos.io'],
                'email_domains': [],
            },
            {
                '_id': 'ucr',
                'name': 'University of California Riverside [Test]',
                'description': 'University of California Riverside [Test]',
                'banner_name': 'ucr-banner.png',
                'logo_name': 'ucr-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('urn:mace:incommon:ucr.edu')),
                'domains': ['test-osf-ucr.cos.io'],
                'email_domains': [],
            },
            {
                '_id': 'usc',
                'name': 'University of Southern California [Test]',
                'description': 'University of Southern California [Test]',
                'banner_name': 'usc-banner.png',
                'logo_name': 'usc-shield.png',
                'auth_url': SHIBBOLETH_SP.format(encode_uri_component('urn:mace:incommon:usc.edu')),
                'domains': ['test-osf-usc.cos.io'],
                'email_domains': [],
            },
        ]

    init_app(routes=False)
    with TokuTransaction():
        for inst_data in INSTITUTIONS:
            new_inst, inst_created = update_or_create(inst_data)
            # update the nodes elastic docs, to have current names of institutions. This will
            # only work properly if this file is the only thign changing institution attributes
            if not inst_created:
                nodes = Node.find_by_institution(new_inst, query=Q('is_deleted', 'ne', True))
                for node in nodes:
                    update_node(node, async=False)
        for extra_inst in Institution.find(Q('_id', 'nin', [x['_id'] for x in INSTITUTIONS])):
            logger.warn('Extra Institution : {} - {}'.format(extra_inst._id, extra_inst.name))


if __name__ == '__main__':
    env = str(sys.argv[1]).lower() if len(sys.argv) == 2 else None
    if env not in ENVS:
        print('An environment must be specified : {}', ENVS)
        sys.exit(1)
    main(env)
