# -*- coding: utf-8 -*-
import logging

from webassets import Environment, Bundle

from website import settings

logger = logging.getLogger(__name__)

env = Environment(settings.STATIC_FOLDER, settings.STATIC_URL_PATH)

css = Bundle(
    # Vendorized libraries
    Bundle(
        'vendor/bower_components/jquery.tagsinput/jquery.tagsinput.css',
        'vendor/pygments.css',
        'vendor/bower_components/x-editable/dist/bootstrap3-editable/css/bootstrap-editable.css',
        'vendor/bower_components/bootstrap/dist/css/bootstrap-theme.css',
        'vendor/bower_components/hgrid/dist/hgrid.css',
        filters='cssmin'),
    # Site-specific CSS
    Bundle(
        'css/site.css',
        'css/rubeus.css',
        'css/commentpane.css',
        'vendor/animate/animate-tasteful.min.css',
        filters="cssmin"),
    output="public/css/common.css"
)


js = Bundle(
    # Vendorized libraries that are already minified
    Bundle(
        # For unknown reasons, moment must be first
        "vendor/bower_components/moment/min/moment-with-langs.min.js",
        "vendor/bower_components/bootstrap/dist/js/bootstrap.min.js",
        "vendor/bootbox/bootbox.min.js",
        "vendor/script.min.js",
    ),
    'vendor/knockout-sortable/knockout-sortable.js',
    'js/site.js',
    "vendor/bower_components/bootstrap.growl/bootstrap-growl.min.js",
    'js/growlBox.js',
    'js/koHelpers.js',
    'js/language.js',
    output="public/js/common.js"
)

js_bottom = Bundle(
    # Vendorized libraries loaded at the bottom of the page
    "vendor/bower_components/x-editable/dist/bootstrap3-editable/js/bootstrap-editable.min.js",
    "vendor/bower_components/jquery.tagsinput/jquery.tagsinput.min.js",
    "vendor/jquery-blockui/jquery.blockui.js",
    # 'vendor/dropzone/dropzone.js',
    # 'vendor/hgrid/hgrid.js',
    'vendor/bower_components/jquery-autosize/jquery.autosize.min.js',
    # Site-specific JS
    Bundle(
        'js/project.js',
        'js/addons.js'
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
