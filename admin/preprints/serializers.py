from osf.models import PreprintContributor


def serialize_withdrawal_request(request):

    return {
        'id': request._id,
        'created': request.created,
        'modified': request.modified,
        'creator': request.creator,
        'comment': request.comment,
        'preprint': request.target,
        'state': request.machine_state,
        'date_last_transitioned': request.date_last_transitioned,
    }

def serialize_simple_user_and_preprint_permissions(preprint, user):
    return {
        'id': user._id,
        'name': user.fullname,
        'permission': PreprintContributor.objects.get(preprint=preprint, user=user).permission
    }
