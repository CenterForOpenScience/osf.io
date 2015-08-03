## TODO: Only seems to be referenced in show_comments.mako. Is this deprecated?
<div
        class="accordion"
        id="comments-${guid}"
        % if not top:
            style="margin-left: 50px;"
        % endif
    >

    <div mod-meta='{
            "tpl": "metadata/show_comments.mako",
            "uri": "/api/v1/guid/${guid}/comments/",
            "replace": true
        }'></div>

    <div mod-meta='{
            "tpl": "metadata/add_comment.mako",
            "uri": "/api/v1/metadata/node/comment/",
            "kwargs": {
                "guid": "${guid}"
            },
            "replace": true
        }'></div>

</div>
