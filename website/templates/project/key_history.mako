<%inherit file="base.mako"/>
<%def name="title()">Key History</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div mod-meta='{
        "tpl": "util/render_key_history.html",
        "uri": "${node_api_url}keys/",
        "kwargs": {
            "route": "${node_api_url}"
        },
        "replace": true
    }'></div>
</%def>
