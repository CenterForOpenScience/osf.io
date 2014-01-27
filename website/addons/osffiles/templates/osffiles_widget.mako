<%inherit file="project/addon/widget.mako"/>

<div mod-meta='{
        "tpl": "util/render_file_tree.mako",
        "uri": "${node['api_url']}files/",
        "kwargs": {
              "dash": true
        },
        "replace": true
    }'></div>
