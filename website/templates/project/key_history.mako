<%inherit file="base.mako"/>
<%def name="title()">Key History</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div mod-meta='{
        "tpl": "util/render_key_history.html",
        "uri": "${node["api_url"]}keys/",
        "kwargs": {
            "route": "${node["api_url"]}"
        },
        "replace": true
    }'></div>
</%def>
