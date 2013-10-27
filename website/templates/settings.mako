<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>
<h2>Profile</h2>

<div mod-meta='{
        "tpl": "util/render_keys.mako",
        "uri": "/api/v1/settings/keys/",
        "replace": true,
        "kwargs" : {
            "route": "/settings/"}
        }'></div>

</%def>
