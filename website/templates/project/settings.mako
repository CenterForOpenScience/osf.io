<%inherit file="base.mako"/>
<%def name="title()">Project Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<!-- Delete node -->
<button id="delete-node" class="btn btn-danger">Delete ${node['category']}</button>
<div class="col-md-6">

    <button id="private-link" class="private-link">Generate Private Link</button>
    % for link in node['private_link']:
        <li
            % if user['can_edit']:
               class="contributor-list-item list-group-item"
            % endif
                >
            <a class="remove-private-link btn btn-default " >-</a>
            <a class="name" style="">${node['url']}?key=${link}/</a>

        </li>
    % endfor
</div>
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

    $('#private-link').on('click', function() {
        $.ajax({
                type:"get",
                url:nodeApiUrl+"generate_private_link",
                contentType:"application/json",
                dataType:"json",
                success:function(){
                    window.location.reload();
                }
        });
    });

    $(".remove-private-link").on("click",function(){
        
        $.ajax({
                type:"POST",
                url:nodeApiUrl+"remove_private_link",
                data:JSON.stringify()
                contentType:"application/json",
                dataType:"json",
                success:function(){
                    window.location.reload();
                }
        })
    });
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
