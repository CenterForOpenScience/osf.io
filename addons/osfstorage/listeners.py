"""
Listens for actions to be done to OSFstorage file nodes specifically.
"""
from website.project.signals import contributor_removed

@contributor_removed.connect
def checkin_files_by_user(node, user):
    """ Listens to a contributor being removed to check in all of their files
    """
    # If user doesn't have any permissions through their OSF group or through contributorship,
    # check their files back in
    if not node.is_contributor_or_group_member(user):
        node.files.filter(checkout=user).update(checkout=None)
