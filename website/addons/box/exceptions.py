from website.addons.base.exceptions import AddonError


class BoxDriveError(AddonError):
    pass


class ExpiredAuthError(BoxDriveError):
    pass
