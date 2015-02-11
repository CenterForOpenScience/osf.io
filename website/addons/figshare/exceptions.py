from website.util.sanitize import escape_html
from website.addons.base.exceptions import AddonEnrichmentError


class FigshareIsDraftError(AddonEnrichmentError):

    def __init__(self, file_guid):
        self.file_guid = file_guid

    @property
    def can_delete(self):
        return True

    @property
    def renderable_error(self):
        return '''
        <div class="alert alert-info" role="alert">
        The file "{name}" is still a draft on Figshare. <br>
        To view it  on the OSF <a href="http://figshare.com/faqs">publish</a> it on Figshare.
        </div>
        '''.format(name=escape_html(self.file_guid.name))
