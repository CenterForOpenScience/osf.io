import httplib as http

from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

from ..api import Figshare  # noqa

@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_widget(*args, **kwargs):

    figshare = kwargs['node_addon']

    #TODO throw error
    # if not figshare.figshare_id:

    if figshare:
        rv = {
            'complete': True,
            'figshare_id': figshare.figshare_id,
            'src': figshare.embed_url,
            'width': figshare_settings.IFRAME_WIDTH,  # noqa
            'height': figshare_settings.IFRAME_HEIGHT,  # noqa
        }
        rv.update(figshare.config.to_json())
        return rv
    raise HTTPError(http.NOT_FOUND)
