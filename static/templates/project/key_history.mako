<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div mod-meta='{
        "tpl": "util/render_key_history.html",
        "uri": "${node_api_url}keys/",
        "kwargs": {
            "route": "${node_api_url}"
        },
        "replace": true
    }'></div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>