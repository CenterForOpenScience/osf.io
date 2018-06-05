from admin.nodes.serializers import serialize_node
from osf.models import PreprintContributor

def serialize_preprint(preprint):

    return {
        'id': preprint._id,
        'title': preprint.title,
        'date_created': preprint.created,
        'modified': preprint.modified,
        'provider': preprint.provider,
        'node': serialize_node(preprint.node) if preprint.node else None,
        'contributors': [serialize_simple_user_and_preprint_permissions(preprint, user) for user in preprint.contributors],
        'is_published': preprint.is_published,
        'date_published': preprint.date_published,
        'subjects': preprint.subjects.all(),
        'is_public': preprint.is_public,
        'creator': preprint.creator._id,
        'deleted': preprint.deleted,
        'verified_publishable': preprint.verified_publishable,
    }

def serialize_simple_user_and_preprint_permissions(preprint, user):
    return {
        'id': user._id,
        'name': user.fullname,
        'permission': PreprintContributor.objects.get(preprint=preprint, user=user).permission
    }
