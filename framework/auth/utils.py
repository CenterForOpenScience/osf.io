import re
from nameparser.parser import HumanName
from modularodm.exceptions import ValidationError

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
    if len(email) > 254:
        raise ValidationError('Invalid Email')

    if not email or '@' not in email:
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
