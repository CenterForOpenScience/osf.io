<ul class="list-group ${'sortable' if sortable and user_can_edit else ''}">

    % for node in nodes:
        <div mod-meta='{
                "tpl": "util/render_node.mako",
                "uri": "${node['api_url']}get_summary/",
                "view_kwargs": {
                    "rescale_ratio" : ${rescale_ratio},
                    "uid" : "${user_id}"
                },
                "replace": true
            }'></div>
    % endfor

</ul>

<!-- Build tooltips on user activity widgets -->
<script>
    $('.ua-meter').tooltip();
</script>

% if sortable and user_can_edit:

    <script>
        $(function(){
            $('.sortable').sortable({
                containment: "#containment",
                tolerance: "pointer",
                items: "> li",
                stop: function(event, ui){
                    var sort_list_elm = this;
                    var id_list = $(sort_list_elm).sortable("toArray", {
                       attribute: "node_id"
                    });
                    checkListChange(id_list, sort_list_elm);
                }
            });
        });
        function checkListChange(id_list, item){
            var data_to_send = {};
            data_to_send['new_list'] = JSON.stringify(id_list);
            $.post('${node_api_url}reorder_components/', data_to_send, function(response){
                if(response['success']=='false'){
                    $(item).sortable("cancel");
                }
            });
        };
    </script>

% endif
