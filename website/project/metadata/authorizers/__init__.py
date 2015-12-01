import json
import os
import logging

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.realpath(__file__))

groups = json.load(
    open(
        os.path.join(HERE, 'defaults.json')
    )
)
fp = None
try:
    fp = open('{0}/local.json'.format(HERE))
except IOError:
    logger.info('No local.json found to populate lists of DraftRegistrationApproval authorizers.')
if fp:
    for group, members in json.load(fp).iteritems():
        if group not in groups:
            groups[group] = members
        else:
            groups[group] = set(groups[group]) | set(members)
    fp.close()

def members_for(group):
    global_members = set(groups['global'])
    return global_members | set(groups.get(group, []))
