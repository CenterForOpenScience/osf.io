from furl import furl
from django.utils import timezone

from framework.auth.core import generate_verification_key
from website import settings, mails


def send_password_reset_email(user, email, verification_type='password', institutional=False, **mail_kwargs):
    """Generate a password reset token, save it to the user and send the password reset email.
    """
    # new verification key (v2)
    user.verification_key_v2 = generate_verification_key(verification_type=verification_type)
    user.email_last_sent = timezone.now()
    user.save()

    reset_link = furl(settings.DOMAIN).add(path=f'resetpassword/{user._id}/{user.verification_key_v2["token"]}').url
    mail_template = mails.FORGOT_PASSWORD if not institutional else mails.FORGOT_PASSWORD_INSTITUTION

    mails.send_mail(
        to_addr=email,
        mail=mail_template,
        reset_link=reset_link,
        can_change_preferences=False,
        **mail_kwargs,
    )

    return reset_link
