<%inherit file="base.mako"/>
<%def name="title()">Project Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<!-- Delete node -->
% if user['is_contributor']:
    % if not node['is_registration']:
    <button id="delete-node" class="btn btn-danger">Delete ${node['category']}</button>
    % endif
<div class="col-md-6" id="linkScope">
    <button id="generate-private-link" class="private-link" data-toggle="modal" href="#private-link">Generate Private Link</button>
    % for link in node['private_links']:
        <li
            % if user['can_edit']:
               class="contributor-list-item list-group-item"
            % endif
                >
            <a class="remove-private-link btn btn-default" data-link="${link}">-</a>
            <a class="link-name" >${node['absolute_url']}?key=${link}/</a>

        </li>
    % endfor
</div>
<%include file="modal_generate_private_link.mako"/>
% endif

##<!-- Show API key settings -->
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "${node["api_url"]}keys/",
##        "replace": true,
##        "kwargs": {
##            "route": "${node["url"]}"
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
            '<div>Delete this ${node["category"]} and all non-project children? This is IRREVERSIBLE.</div>' +
                '<p style="font-weight: normal; font-size: medium; line-height: normal;">If you want to continue, type <strong>' + key + '</strong> and click OK.</p>',
            function(result) {
                if (result === key) {
                    window.location.href = '${node["url"]}remove/';
                }
            }
        )
    });
</script>
</%def>
