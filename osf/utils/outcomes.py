from enum import IntEnum


class NoPIDError(Exception):
    pass


class ArtifactTypes(IntEnum):
    '''Labels used to classify artifacts.

    Gaps are to allow space for new value to be added later while
    controlling for display order.

    PRIMARY value is arbitrarily large as it is an internal-only concept for now
    '''
    UNDEFINED = 0
    DATA = 1
    CODE = 11
    MATERIALS = 21
    PAPERS = 31
    SUPPLEMENTS = 41
    PRIMARY = 1001

    @classmethod
    def choices(cls):
        return tuple((entry.value, entry.name) for entry in cls)
