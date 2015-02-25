from website.addons.base import AddonError


class GoogleDriveError(AddonError):
    pass


class ExpiredAuthError(GoogleDriveError):
    pass
