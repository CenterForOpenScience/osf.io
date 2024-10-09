from osf.models import OSFUser
from django.core.exceptions import ValidationError

def get_or_refresh_confirmation_link(uid):
    u = OSFUser.load(uid)
    if u.is_confirmed:
        return {'error': f'User {uid} is already confirmed'}

    if u.deleted or u.is_merged:
        return {'error': f'User {uid} is deleted or merged'}

    try:
        confirmation_link = u.get_or_create_confirmation_url(u.username, force=True, renew=True)
        return {'confirmation_link': confirmation_link}
    except ValidationError:
        return {'error': f'Invalid email for user {uid}'}
    except KeyError:
        return {'error': 'Could not generate or refresh confirmation link'}
