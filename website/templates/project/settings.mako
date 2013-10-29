<%inherit file="base.mako"/>
<%def name="title()">Project Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<!-- Delete node -->
<button id="delete-node" class="btn btn-danger">Delete ${node_category}</button>

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

<%def name="javascript_bottom()">
<script type="text/javascript">
    ## TODO: Replace with something more fun, like the name of a famous scientist
    ## h/t @sloria
    function randomString() {
        var alphabet = 'abcdefghijkmnpqrstuvwxyz23456789',
            text = '';

        for (var i = 0; i < 5; i++)
            text += alphabet.charAt(Math.floor(Math.random() * alphabet.length));

        return text;
    }

    $('#delete-node').on('click', function() {
        var key = randomString();
        bootbox.prompt(
            '<div>Delete this ${node_category} and all non-project children? This is IRREVERSIBLE.</div>' +
                '<p style="font-weight: normal; font-size: medium; line-height: normal;">If you want to continue, type <strong>' + key + '</strong> and click OK.</p>',
            function(result) {
                if (result === key) {
                    window.location.href = '${node_url}remove/';
                }
            }
        )
    });
</script>
</%def>
