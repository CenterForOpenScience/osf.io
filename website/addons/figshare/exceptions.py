from website.addons.base.exceptions import AddonEnrichmentError

class FigshareIsDraftError(AddonEnrichmentError):

    @property
    def renderable_error(self):
        return '''<p>This File is still a draft on Figshare, to view it publish it or go here</p>'''

