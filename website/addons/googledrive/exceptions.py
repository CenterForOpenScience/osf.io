from website.addons.base.exceptions import AddonError


class GoogleDriveError(AddonError):
    pass


class ExpiredAuthError(GoogleDriveError):
    pass
