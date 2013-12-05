"""

"""

from website.app import init_app
from website import models
from framework import Q

app = init_app()

known_schemas = [
    'Open-Ended_Registration',
    'OSF-Standard_Pre-Data_Collection_Registration',
    'Replication_Recipe_(Brandt_et_al__!dot!__,_2013):_Pre-Registration',
    'Replication_Recipe_(Brandt_et_al__!dot!__,_2013):_Post-Completion',
]

def find_bad_registrations():
    """Find registrations with unexpected numbers of template keys or
    outdated templates.

    """
    registrations = models.Node.find(
        Q('is_registration', 'eq', True)
    )
    for registration in registrations:
        meta = registration.registered_meta or {}
        keys = meta.keys()
        if len(keys) != 1:
            print 'Inconsistency: Number of keys on project {} ({}) != 1'.format(
                registration.title,
                registration._primary_key,
            )
            continue
        if keys[0] not in known_schemas:
            print 'Inconsistency: Registration schema {} on project {} ({}) not in known schemas'.format(
                keys[0],
                registration.title,
                registration._primary_key,
            )

if __name__ == '__main__':
    find_bad_registrations()
