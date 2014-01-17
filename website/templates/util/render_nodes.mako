<ul class="list-group ${'sortable' if sortable and user['can_edit'] else ''}">
    % for each in nodes:
        <div mod-meta='{
                "tpl": "util/render_node.mako",
                "uri": "${each['api_url']}get_summary/",
                "view_kwargs": {
                    "rescale_ratio": ${rescale_ratio},
                    "uid": "${user_id}"
                },
                "replace": true
            }'></div>
    % endfor
## TODO: make sure these templates are only included once on a page.
<%include file='log_templates.mako'/>
</ul>

% if sortable and user['can_edit']:

    <script>

        $(function(){
            $('.sortable').sortable({
                containment: '#containment',
                tolerance: 'pointer',
                items: '> li',
                stop: function(event, ui){
                    var sortListElm = this;
                    var idList = $(sortListElm).sortable(
                        'toArray',
                        {attribute: 'node_reference'}
                    );
                    checkListChange(idList, sortListElm);
                }
            });
        });

        function checkListChange(idList, elm){
            $.ajax({
                type: 'POST',
                url: '${node['api_url']}reorder_components/',
                data: JSON.stringify({'new_list': idList}),
                contentType: 'application/json',
                dataType: 'json',
                fail: function() {
                    $(elm).sortable('cancel');
                }
            });
        }

    </script>
% endif
