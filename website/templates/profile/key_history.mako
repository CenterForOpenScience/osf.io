<%inherit file="base.mako"/>
<%def name="title()">Key History</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>

<div mod-meta='{
        "tpl": "util/render_key_history.mako",
        "uri": "/api/v1/settings/key_history/${key}/",
        "replace": true
    }'></div>
</%def>

