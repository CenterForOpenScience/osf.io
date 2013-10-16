<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<!-- Delete node -->
<script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.0.0/bootbox.min.js"></script>
<button id="delete-node" class="btn primary">Delete ${node_category}</button>
<script type="text/javascript">
    $('#delete-node').on('click', function() {
        bootbox.prompt(
            '<div>Delete this ${node_category} and all non-project children</div>' +
                '<div style="font-weight: normal; font-size: medium; line-height: normal;">If you want to continue, type the project title below and click OK</div>',
            function(result) {
                if (result === '${node_title}') {
                    window.location.href = '${node_url}remove/';
                } else {
                    bootbox.alert('Component not deleted');
                }
            }
        )
    });
</script>

<!-- Show API key settings -->
<div mod-meta='{
        "tpl": "util/render_keys.mako",
        "uri": "${node_api_url}keys/",
        "replace": true,
        "kwargs": {
            "route": "${node_url}"
        }
    }'></div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>
