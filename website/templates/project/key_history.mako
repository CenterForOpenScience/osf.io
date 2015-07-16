## TODO: Is this used anywhere?

<%inherit file="project/project_base.mako"/>
<%def name="title()">Key History</%def>

<div mod-meta='{
        "tpl": "util/render_key_history.html",
        "uri": "${node["api_url"]}keys/",
        "kwargs": {
            "route": "${node["api_url"]}"
        },
        "replace": true
    }'></div>
