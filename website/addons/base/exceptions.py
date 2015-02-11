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
        return '''
        <div class="alert alert-info" role="alert">
        This file is currently unable to be rendered. <br>
        If this should not have occurred and the issue persists,
        please report it to <a href="mailto:support@osf.io">support@osf.io
        </div>
        '''
