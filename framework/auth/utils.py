from rest_framework import status as http_status
import re

from nameparser.parser import HumanName
import requests

from django.apps import apps
from django.core.exceptions import ValidationError

from website import settings

# email verification adopted from django. For licence information, see NOTICE
USER_REGEX = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*$"  # dot-atom
    # quoted-string
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]'
    r'|\\[\001-\011\013\014\016-\177])*"$)', re.IGNORECASE)

DOMAIN_REGEX = re.compile(
    # domain
    r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
    r'(?:[A-Z]{2,6}|[A-Z0-9-]{2,})$'
    # literal form, ipv4 address (SMTP 4.1.3)
    r'|^\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)'
    r'(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$', re.IGNORECASE)


def validate_email(email):
    BlacklistedEmailDomain = apps.get_model('osf.BlacklistedEmailDomain')
    if len(email) > 254:
        raise ValidationError('Invalid Email')

    if not email or '@' not in email:
        raise ValidationError('Invalid Email')

    domain = email.split('@')[1].lower()
    if BlacklistedEmailDomain.objects.filter(domain=domain).exists():
        raise ValidationError('Invalid Email')

    user_part, domain_part = email.rsplit('@', 1)

    if not USER_REGEX.match(user_part):
        raise ValidationError('Invalid Email')

    if not DOMAIN_REGEX.match(domain_part):
        try:
            domain_part = domain_part.encode('idna').decode('ascii')
        except UnicodeError:
            pass
        else:
            if DOMAIN_REGEX.match(domain_part):
                return True
        raise ValidationError('Invalid Email')

    return True


def impute_names(name):
    human = HumanName(name)
    return {
        'given': human.first,
        'middle': human.middle,
        'family': human.last,
        'suffix': human.suffix,
    }


def impute_names_model(name):
    human = HumanName(name)
    return {
        'given_name': human.first,
        'middle_names': human.middle,
        'family_name': human.last,
        'suffix': human.suffix,
    }


def privacy_info_handle(info, anonymous, name=False):
    """hide user info from api if anonymous

    :param str info: info which suppose to return
    :param bool anonymous: anonymous or not
    :param bool name: if the info is a name,
    :return str: the handled info should be passed through api

    """
    if anonymous:
        return 'A user' if name else ''
    return info


def ensure_external_identity_uniqueness(provider, identity, user=None):
    from osf.models import OSFUser
    users_with_identity = OSFUser.objects.filter(
        **{'external_identity__{}__{}__isnull'.format(provider, identity): False}
    )
    for existing_user in users_with_identity:
        if user and user._id == existing_user._id:
            continue
        if existing_user.external_identity[provider][identity] == 'VERIFIED':
            if user and user.external_identity.get(provider, {}).get(identity, {}):
                user.external_identity[provider].pop(identity)
                if user.external_identity[provider] == {}:
                    user.external_identity.pop(provider)
                user.save()  # Note: This won't work in v2 because it rolls back transactions when status >= 400
            raise ValidationError('Another user has already claimed this external identity')
        existing_user.external_identity[provider].pop(identity)
        if existing_user.external_identity[provider] == {}:
            existing_user.external_identity.pop(provider)
        existing_user.save()
    return


def validate_recaptcha(response, remote_ip=None):
    """
    Validate if the recaptcha response is valid.

    :param response: the recaptcha response form submission
    :param remote_ip: the remote ip address
    :return: True if valid, False otherwise
    """
    if not response:
        return False
    payload = {
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': response,
    }
    if remote_ip:
        payload.update({'remoteip': remote_ip})
    resp = requests.post(settings.RECAPTCHA_VERIFY_URL, data=payload)
    return resp.status_code == http_status.HTTP_200_OK and resp.json().get('success')


def generate_csl_given_name(given_name, middle_names='', suffix=''):
    parts = [given_name]
    if middle_names:
        middle_names = middle_names.strip()
        parts.extend(each[0] for each in re.split(r'\s+', middle_names))
    given = ' '.join(parts)
    if suffix:
        given = '%s, %s' % (given, suffix)
    return given
