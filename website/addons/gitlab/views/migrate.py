from website.project.model import (
    contributor_added, contributor_removed, permission_changed
)

@contributor_added.connect
@contributor_removed.connect
@permission_changed.connect
def gitlab_flag_dirty(node, **kwargs):
    """Flag migration as dirty if configuration changes. Note: should be
    deleted once overall migration is complete.

    """
    node_addon = node.get_addon('gitlab')
    if node_addon:
        node_addon._migration_done = False
        node_addon.save()
