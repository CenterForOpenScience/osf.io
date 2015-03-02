"""
Custom exceptions for add-ons.
"""


class AddonError(Exception):
    pass


class HookError(AddonError):
    pass


class AddonEnrichmentError(AddonError):

    @property
    def can_delete(self):
        return False

    @property
    def can_download(self):
        return False

    @property
    def renderable_error(self):
        '''A hook to be implemented by subclasses returning
        a html error to be displayed to the user
        Later concatenated with additional style tags
        '''
        return '''
        <div class="alert alert-info" role="alert">
        This file is currently unable to be rendered. <br>
        If this should not have occurred and the issue persists,
        please report it to <a href="mailto:support@osf.io">support@osf.io
        </div>
        '''

    def as_html(self):
        # TODO Refactor me to be all in the front end
        # 2/10/14 ping @chrisseto when refactoring
        additional = ''
        if not self.can_download:
            additional += "<style>.file-download{display: none;}</style>"

        if not self.can_delete:
            additional += "<style>.file-delete{display: none;}</style>"

        return self.renderable_error + additional


class FileDeletedError(AddonEnrichmentError):

    @property
    def renderable_error(self):
        return '''
        <div class="alert alert-info" role="alert">
        This file has been deleted.
        </div>
        '''


class FileDoesntExistError(AddonEnrichmentError):

    @property
    def renderable_error(self):
        return '''
        <div class="alert alert-info" role="alert">
        This file does not exist.
        </div>
        '''
