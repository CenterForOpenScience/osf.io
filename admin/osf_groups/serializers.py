

def serializer_group(osf_group):

    return {
        'named_id': osf_group._id,
        'name': osf_group.name,
        'created': osf_group.created,
        'modified': osf_group.modified,
        'creator': osf_group.creator,
        'managers': list(osf_group.managers.all()),
        'members': list(osf_group.members.all()),
        'nodes': list(osf_group.nodes)
    }
