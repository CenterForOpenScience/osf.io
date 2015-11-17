'''
Listens for actions to be done to OSFstorage file nodes specifically.
'''
from modularodm import Q

from website.project import signals as project_signals
from website.files.models.osfstorage import OsfStorageFileNode

@project_signals.contributor_removed.connect
def checkin_files_by_user(node, user):
    ''' Listens to a contributor being removed to check in all of their files
    '''
    files = OsfStorageFileNode.find(Q('node', 'eq', node) & Q('checkout', 'eq', user))
    for file in files:
        file.checkout = None
        file.save()
