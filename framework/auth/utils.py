from nameparser.parser import HumanName


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
