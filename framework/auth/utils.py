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
