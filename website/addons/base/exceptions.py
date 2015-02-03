"""
Custom exceptions for add-ons.
"""


class AddonError(Exception):
    pass


class HookError(AddonError):
    pass


class AddonEnrichmentError(AddonError):

    @property
    def renderable_error(self):
        return 'TODO'
