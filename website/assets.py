# -*- coding: utf-8 -*-
import logging

from webassets import Environment, Bundle
from webassets.filter import get_filter

from website import settings

logger = logging.getLogger(__name__)

env = Environment(settings.STATIC_FOLDER, settings.STATIC_URL_PATH)

css = Bundle(
            "css/site.css",
            filters="cssmin",
            output="public/css/common.css"
)

css_vendor = Bundle(
            "vendor/jquery-ui/css/jquery-ui.css",
            "vendor/jquery-tagit/css/jquery.tagit.css",
            "vendor/jquery-tagsinput/css/jquery.tagsinput.css",
            "vendor/jquery-tagit/css/tagit.ui-zendesk.css",
            "vendor/jquery-treeview/jquery.treeview.css",
            "vendor/jquery-fileupload/css/jquery.fileupload-ui.css",
            "vendor/pygments.css",
            "vendor/bootstrap-editable/css/bootstrap-editable.css",
            filters="cssmin",
            output="public/css/vendor.css"
)

js = Bundle(
            "js/site.js",
            filters="jsmin",
            output="public/js/common.js")

# Vendorized libraries that are already minified
js_vendor = Bundle(
        "vendor/jquery/jquery.min.js",
        "vendor/jquery-ui/js/jquery-ui.min.js",
        "vendor/bootstrap2/js/bootstrap.min.js",
        "vendor/bootstrap-editable/js/bootstrap-editable.min.js",
        "vendor/bootbox/bootbox.min.js",
        "vendor/jquery-tagsinput/js/jquery.tagsinput.min.js",
        "vendor/jquery-tagcloud/jquery.tagcloud.js",
        "vendor/jquery-treeview/jquery.treeview.js",
        "vendor/jquery-tagit/js/tag-it.js",
        output="public/js/vendor.js"
)

logger.debug("Registering asset bundles")
env.register("js", js)
env.register("js_vendor", js_vendor)
env.register("css", css)
env.register("css_vendor", css_vendor)
