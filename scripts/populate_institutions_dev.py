#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with Institution fixtures."""
from website.app import init_app
from website.models import Institution
from framework.transactions.context import TokuTransaction


INSTITUTIONS = [
    {
        'name': 'Virginia Tech',
        '_id': 'VT',
        'logo_name': 'virginia-tech.jpg',
        'auth_url': 'https://login.vt.test',
    },
    {
        'name': 'Notre Dame',
        '_id': 'ND',
        'logo_name': 'notre-dame.jpg',
        'auth_url': 'https://login.nd.test',
    }
]

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

def main():
    init_app(routes=False)
    for inst_data in INSTITUTIONS:
        with TokuTransaction():
            new_inst, inst_created = update_or_create(inst_data)


if __name__ == '__main__':
    main()
