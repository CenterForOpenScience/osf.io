'''
Listens for actions to be done to OSFstorage file nodes specifically.
'''
from modularodm import Q

from website.project.signals import contributor_removed
from website.files.models.osfstorage import OsfStorageFileNode

@contributor_removed.connect
def checkin_files_by_user(user, node):
    ''' Listens to a contributor being removed to check in all of their files
    '''
    files = OsfStorageFileNode.find(Q('node', 'eq', node) & Q('checkout', 'eq', user))
    for file in files:
        file.checkout = None
        file.save()
