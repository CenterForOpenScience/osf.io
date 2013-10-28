<%inherit file="base.mako"/>
<%def name="title()">Project Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<!-- Delete node -->
<button id="delete-node" class="btn btn-danger">Delete ${node_category}</button>
<script type="text/javascript">
    $('#delete-node').on('click', function() {
        bootbox.prompt(
            '<div>Delete this ${node_category} and all non-project children</div>' +
                '<div style="font-weight: normal; font-size: medium; line-height: normal;">If you want to continue, type the project title below and click OK</div>',
            function(result) {
                if (result === '${node_title}') {
                    window.location.href = '${node_url}remove/';
                }
            }
        )
    });
</script>

##<!-- Show API key settings -->
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "${node_api_url}keys/",
##        "replace": true,
##        "kwargs": {
##            "route": "${node_url}"
##        }
##    }'></div>
</%def>
