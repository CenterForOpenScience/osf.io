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

logger.debug('Registering asset bundles')
env.register('css', css)
# Don't bundle in debug mode
env.debug = settings.DEBUG_MODE
