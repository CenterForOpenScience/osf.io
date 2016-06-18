# -*- coding: utf-8 -*-
"""Get public registrations for staff members.

    python -m scripts.staff_public_regs
"""
from collections import defaultdict
import logging

from modularodm import Q

from website.models import Node, User
from website.app import init_app

logger = logging.getLogger('staff_public_regs')

STAFF_GUIDS = [
    'jk5cv',  # Jeff
    'cdi38',  # Brian
    'edb8y',  # Johanna
    'hsey5',  # Courtney
    '5hdme',  # Melissa
]

def main():
    init_app(set_backends=True, routes=False)
    staff_registrations = defaultdict(list)
    users = [User.load(each) for each in STAFF_GUIDS]
    for registration in Node.find(Q('is_registration', 'eq', True) & Q('is_public', 'eq', True)):
        for user in users:
            if registration in user.contributed:
                staff_registrations[user._id].append(registration)

    for uid in staff_registrations:
        user = User.load(uid)
        user_regs = staff_registrations[uid]
        logger.info('{} ({})  on {} Public Registrations:'.format(
            user.fullname,
            user._id,
            len(user_regs))
        )
        for registration in user_regs:
            logger.info('\t{} ({}): {}'.format(registration.title,
                registration._id,
                registration.absolute_url)
            )

if __name__ == '__main__':
    main()
