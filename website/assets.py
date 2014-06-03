# -*- coding: utf-8 -*-
import logging

from webassets import Environment, Bundle

from website import settings

logger = logging.getLogger(__name__)

env = Environment(settings.STATIC_FOLDER, settings.STATIC_URL_PATH)

css = Bundle(
        # Vendorized libraries
         Bundle(
            'vendor/jquery-tagit/css/jquery.tagit.css',
            'vendor/jquery-tagsinput/css/jquery.tagsinput.css',
            'vendor/jquery-tagit/css/tagit.ui-zendesk.css',
            'vendor/jquery-fileupload/css/jquery.fileupload-ui.css',
            'vendor/pygments.css',
            'vendor/bootstrap3-editable/css/bootstrap-editable.css',
            'vendor/bower_components/bootstrap/dist/css/bootstrap-theme.css',
            'vendor/bower_components/hgrid/dist/hgrid.css',
            filters='cssmin'),
        # Site-specific CSS
        Bundle(
            'css/site.css',
            'css/rubeus.css',
            'css/commentpane.css',
            filters="cssmin"),
        output="public/css/common.css"
)


js = Bundle(
    # Vendorized libraries that are already minified
    Bundle(
        "vendor/bower_components/bootstrap/dist/js/bootstrap.min.js",
        "vendor/bootbox/bootbox.min.js",
        "vendor/script.min.js",
    ),
    output="public/js/common.js"
)

js_bottom = Bundle(
    # Vendorized libraries loaded at the bottom of the page
    "vendor/bootstrap3-editable/js/bootstrap-editable.min.js",
    "vendor/jquery-tagsinput/js/jquery.tagsinput.min.js",
    "vendor/jquery-tagcloud/jquery.tagcloud.js",
    "vendor/jquery-tagit/js/tag-it.js",
    "vendor/bower_components/momentjs/min/moment.min.js",
    "vendor/jquery-blockui/jquery.blockui.js",
    'vendor/knockout-sortable/knockout-sortable.js',
    # 'vendor/dropzone/dropzone.js',
    # 'vendor/hgrid/hgrid.js',
    'vendor/autosize/jquery.autosize.min.js',
    # Site-specific JS
    Bundle('js/site.js',
            'js/language.js',
            'js/project.js',
            'js/app.js',
            'js/addons.js',
            # 'js/dropzone-patch.js',
            # 'js/rubeus.js'
            ),
    filters='jsmin',
    output='public/js/site.js'
)


logger.debug('Registering asset bundles')
env.register('js', js)
env.register('css', css)
env.register('js_bottom', js_bottom)
# Don't bundle in debug mode
env.debug = settings.DEBUG_MODE
