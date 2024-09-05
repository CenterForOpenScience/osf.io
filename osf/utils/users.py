from django.utils import timezone
from osf.models import OSFUser
from django.core.exceptions import ValidationError
from website.settings import DOMAIN

def get_or_refresh_confirmation_link(uid):
    u = OSFUser.load(uid)
    if u.is_confirmed:
        return {'error': f'User {uid} is already confirmed'}

    if u.deleted or u.is_merged:
        return {'error': f'User {uid} is deleted or merged'}

    confirmation_link = None
    if u.emails.filter(address=u.username).exists():
        for token, data in u.email_verifications.items():
            if data['email'] == u.username and data['expiration'] < timezone.now():
                u.email_verifications[token]['expiration'] = timezone.now() + timezone.timedelta(days=30)
                u.save()
                confirmation_link = f'{DOMAIN.rstrip("/")}/confirm/{u._id}/{token}'
                return {'confirmation_link': confirmation_link}
    else:
        try:
            u.add_unconfirmed_email(u.username)
            u.save()
            for token, data in u.email_verifications.items():
                if data['email'] == u.username:
                    confirmation_link = f'{DOMAIN.rstrip("/")}/confirm/{u._id}/{token}'
                    return {'confirmation_link': confirmation_link}
        except ValidationError:
            return {'error': f'Invalid email for user {uid}'}

    if confirmation_link:
        return {'confirmation_link': confirmation_link}
    else:
        return {'error': 'Could not generate or refresh confirmation link'}
