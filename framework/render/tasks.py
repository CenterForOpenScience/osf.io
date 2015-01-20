# -*- coding: utf-8 -*-

import os
import logging
import errno
import codecs

from framework.tasks import app
from website import settings
from website.language import ERROR_PREFIX

logger = logging.getLogger(__name__)

import mfr
from mfr.exceptions import MFRError

CUSTOM_ERROR_MESSAGES = {}

# Unable to render. Download the file to view it.
def render_mfr_error(err):
    pre = ERROR_PREFIX
    msg = CUSTOM_ERROR_MESSAGES.get(type(err), err.message)
    return """
           <div class="osf-mfr-error">
           <p>{pre}</p>
           <p>{msg}</p>
           </div>
        """.format(**locals())


@app.task(ignore_result=True, timeout=settings.MFR_TIMEOUT)
def _build_rendered_html(file_path, cache_dir, cache_file_name, download_url):
    """
    :param str file_path: Full path to raw file on disk
    :param str cache_dir: Folder to store cached file in
    :param str cache_file_name: Name of cached file
    :param str download_url: External download URL
    """
    with codecs.open(file_path) as file_pointer:

        # Build path to cached content
        # Note: Ensures that cache directories have the same owner as the files
        # inside them
        ensure_path(cache_dir)
        cache_file_path = os.path.join(cache_dir, cache_file_name)

        with codecs.open(cache_file_path, 'w', 'utf-8') as write_file_pointer:
            # Render file
            try:
                rendered = mfr.render(file_pointer, src=download_url)
                result = _build_html(rendered)
            except MFRError as err:
                result = render_mfr_error(err).format(download_path=download_url)

            # Close read pointer
            #file_pointer.close()

            # Cache rendered content
            write_file_pointer.write(result)

    os.remove(file_path)
    return True

#Expose render function
build_rendered_html = _build_rendered_html

if settings.USE_CELERY:
    build_rendered_html = _build_rendered_html.delay

def _build_css_asset(css_uri):
    """Wrap a css asset so it can be included on an html page"""
    return '<link rel="stylesheet" href={uri}/>'.format(uri=css_uri)

def _build_js_asset(js_uri):
    """Wrap a js asset so it can be included on an html page"""
    return '<script src="{uri}"></script>'.format(uri=js_uri)

def _build_html(render_result):
    """Build all of the assets and content into an html page"""
    if render_result.assets:
        css_list = render_result.assets.get('css') or []
        css_assets = "\n".join(
            [_build_css_asset(css_uri) for css_uri in css_list]
        )

        js_list = render_result.assets.get('js') or []
        js_assets = "\n".join(
            [_build_js_asset(js_uri) for js_uri in js_list]
        )
    else:
        css_assets = js_assets = ""

    rv = "{css}\n\n{js}\n\n{content}".format(
        css=css_assets,
        js=js_assets,
        content=render_result.content or "",
    )

    return rv

def ensure_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
