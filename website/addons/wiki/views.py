"""

"""

from bs4 import BeautifulSoup

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon


@must_be_contributor_or_public
@must_have_addon('wiki')
def wiki_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki = node.get_addon('wiki')
    wiki_page = node.get_wiki_page('home')

    if wiki_page and wiki_page.html:
        wiki_html = wiki_page.html
        if len(wiki_html) > 500:
            wiki_html = BeautifulSoup(wiki_html[:500] + '...', 'html.parser')
        else:
            wiki_html = BeautifulSoup(wiki_html)
    else:
        wiki_html = None

    rv = {
        'complete': True,
        'content': wiki_html,
        'more': False,
    }
    rv.update(wiki.config.to_json())
    return rv
