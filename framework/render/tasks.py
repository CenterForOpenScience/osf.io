# -*- coding: utf-8 -*-
import os
import errno
import codecs
import urllib
import logging

import mfr
from mfr.ext import ALL_HANDLERS
from mfr.exceptions import MFRError

from framework.tasks import app
from website import settings
from website.language import ERROR_PREFIX

logger = logging.getLogger(__name__)

# Ensure all filehandlers are registered. This MUST happen here so that
# the handlers are registered when celery imports this module
mfr.register_filehandlers(ALL_HANDLERS)
# Update mfr config with static path and url
mfr.config.update({
    # Base URL for static files
    'ASSETS_URL': os.path.join(settings.STATIC_URL_PATH, 'mfr'),
    # Where to save static files
    'ASSETS_FOLDER': os.path.join(settings.STATIC_FOLDER, 'mfr'),
})

CUSTOM_ERROR_MESSAGES = {}

# Unable to render. Download the file to view it.
def render_mfr_error(err):
    pre = ERROR_PREFIX
    msg = CUSTOM_ERROR_MESSAGES.get(type(err), err.message)
    return u"""
           <div class="osf-mfr-error">
           <p>{pre}</p>
           <p>{msg}</p>
           </div>
        """.format(**locals())


# TODO only allow one task at a time
@app.task(ignore_result=True, timeout=settings.MFR_TIMEOUT)
def _build_rendered_html(download_url, cache_path, temp_path):
    """
    :param str file_path: Full path to raw file on disk
    :param str cache_dir: Folder to store cached file in
    :param str cache_file_name: Name of cached file
    :param str download_url: External download URL
    """
    try:
        ensure_path(os.path.split(temp_path)[0])
        urllib.urlretrieve(download_url, temp_path)
    except:
        # TODO Log to sentry here
        return

    with codecs.open(temp_path) as file_pointer:

        # Build path to cached content
        # Note: Ensures that cache directories have the same owner as the files
        # inside them
        ensure_path(os.path.split(cache_path)[0])

        with codecs.open(cache_path, 'w', 'utf-8') as write_file_pointer:
            # Render file
            try:
                render_result = mfr.render(file_pointer, src=download_url)
            except MFRError as err:
                rendered = render_mfr_error(err)
            else:
                rendered = _build_html(render_result)

            # Cache rendered content
            write_file_pointer.write(rendered)

    os.remove(temp_path)

#Expose render function
build_rendered_html = _build_rendered_html

if settings.USE_CELERY:
    build_rendered_html = _build_rendered_html.delay

def _build_css_asset(css_uri):
    """Wrap a css asset so it can be included on an html page"""
    return '<link rel="stylesheet" href="{uri}" />'.format(uri=css_uri)

def _build_js_asset(js_uri):
    """Wrap a js asset so it can be included on an html page"""
    return '<script src="{uri}"></script>'.format(uri=js_uri)

def _build_html(render_result):
    """Build all of the assets and content into an html page"""
    if render_result.assets:
        css_list = render_result.assets.get('css') or []
        css_assets = u"\n".join(
            [_build_css_asset(css_uri) for css_uri in css_list]
        )

        js_list = render_result.assets.get('js') or []
        js_assets = u"\n".join(
            [_build_js_asset(js_uri) for js_uri in js_list]
        )
    else:
        css_assets = js_assets = ""

    rv = u"{css}\n\n{js}\n\n{content}".format(
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
