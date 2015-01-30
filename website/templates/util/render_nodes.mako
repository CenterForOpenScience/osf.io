<ul class="list-group ${'sortable' if sortable and 'write' in user['permissions'] else ''}">
    % for each in nodes:
        <div mod-meta='{
                "tpl": "util/render_node.mako",
                "uri": "${each['api_url']}get_summary/",
                "view_kwargs": {
                    "rescale_ratio": ${rescale_ratio},
                    "primary": ${int(each['primary'])},
                    "link_id": "${each['id']}",
                    "uid": "${user_id}"
                },
                "replace": true
            }'></div>
    % endfor
## TODO: make sure these templates are only included once on a page.
<%include file='_log_templates.mako'/>
</ul>
<script>
% if sortable and 'write' in user['permissions']:

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
                    NodeActions.reorderChildren(idList, sortListElm);
                }
            });
        });

% endif

</script>

