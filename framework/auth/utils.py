from nameparser.parser import HumanName


def impute_names(name):
    human = HumanName(name)
    return {
        'given': human.first,
        'middle': human.middle,
        'family': human.last,
        'suffix': human.suffix,
    }
