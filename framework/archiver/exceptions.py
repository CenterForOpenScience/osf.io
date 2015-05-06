class ArchiverError(Exception):
    pass

class AddonArchiverError(ArchiverError):

    def __init__(self, provider, stat_result):
        self.provider = provider
        self.stat_result = stat_result

class AddonFileSizeExceeded(AddonArchiverError):

    pass

class AddonArchiveSizeExceeded(AddonArchiverError):

    pass
