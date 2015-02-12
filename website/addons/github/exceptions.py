from github3 import GitHubError  # noqa

from website.util.sanitize import escape_html
from website.addons.base.exceptions import AddonEnrichmentError


class ApiError(Exception):
    pass


class NotFoundError(ApiError):
    pass


class EmptyRepoError(ApiError):
    pass


class TooBigError(ApiError):
    pass


class TooBigToRenderError(AddonEnrichmentError):

    def __init__(self, file_guid):
        self.file_guid = file_guid

    @property
    def can_delete(self):
        return True

    @property
    def can_download(self):
        return True

    @property
    def renderable_error(self):
        return '''
        <div class="alert alert-info" role="alert">
        The file "{name}" is too large to be retrieved from Github for rendering.
        </div>
        '''.format(name=escape_html(self.file_guid.name))
