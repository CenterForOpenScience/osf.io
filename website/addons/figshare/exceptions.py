from website.addons.base.exceptions import AddonEnrichmentError
from website.util.sanitize import escape_html

class FigshareIsDraftError(AddonEnrichmentError):

    def __init__(self, file_guid):
        self.file_guid = file_guid

    @property
    def renderable_error(self):
        return '''
        <div class="alert alert-info" role="alert">
        The file "{name}" is still a draft on Figshare. <br>
        To view it  on the OSF <a href="http://figshare.com/faqs">publish</a> it on Figshare.
        </div>
        '''.format(name=escape_html(self.file_guid.name))
