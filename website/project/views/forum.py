"""
Forum views.
"""
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project

from website import settings
from furl import furl

@must_be_contributor_or_public
def forum_view(auth, node, **kwargs):
    forum_url = furl(settings.DISCOURSE_SERVER_URL).join('/session/sso')
    data = _view_project(node, auth, primary=True)
    data['forum_url'] = forum_url.url
    return data
