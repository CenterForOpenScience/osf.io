import httplib as http

from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission,
    must_have_write_permission_or_public_wiki,
)

@must_have_addon('dryad', 'node')
def dryad_widget( **kwargs):
    node = kwargs['node'] or kwargs['project']
    pid = kwargs['pid']
    dryad = node.get_addon('dryad')
    widget_url = '/{}/dryad/'.format(pid)#node.api_url_for('browser.dryad_browser')

    ret = {'complete': True,
            'browser_url': widget_url,
            'test_content':str(kwargs) }

    ret.update(dryad.config.to_json() )
    """
    ret = {
        'complete': True,
        'wiki_content': unicode(wiki_html) if wiki_html else None,
        'wiki_content_url': node.api_url_for('wiki_page_content', wname='home'),
        'use_python_render': use_python_render,
        'more': more,
        'include': False,
    }
    ret.update(wiki.config.to_json())
    return ret
    """

    return ret

@must_have_addon('dryad', 'node')
def browser_widget( **kwargs):
    node = kwargs['node'] or kwargs['project']
    pid = kwargs['pid']
    dryad = node.get_addon('dryad')
    widget_url = '/project/{}/dryad/browser'.format(pid)#node.api_url_for('browser.dryad_browser')
    widget_url = '/dryad/browser/'
    ret = {'complete': True,
            'browser_url': widget_url,
            'test_content':str(kwargs) }

    ret.update(dryad.config.to_json() )
    """
    ret = {
        'complete': True,
        'wiki_content': unicode(wiki_html) if wiki_html else None,
        'wiki_content_url': node.api_url_for('wiki_page_content', wname='home'),
        'use_python_render': use_python_render,
        'more': more,
        'include': False,
    }
    ret.update(wiki.config.to_json())
    return ret
    """

    return ret