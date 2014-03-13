from ..exceptions import MFRError


class TooBigTableError(MFRError):
    pass

class BlankOrCorruptTableError(MFRError):
    pass

class StataVersionError(MFRError):
    pass
