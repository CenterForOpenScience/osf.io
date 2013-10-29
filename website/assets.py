# -*- coding: utf-8 -*-
from webassets import Environment, Bundle

from website import settings

env = Environment(settings.STATIC_FOLDER, settings.STATIC_URL_PATH)

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

env.register("js", js)
env.register("js_vendor", js_vendor)
