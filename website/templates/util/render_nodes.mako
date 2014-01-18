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

<script>

    % if sortable and user['can_edit']:

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

    % endif

    function removePointer(pointerId, pointerElm) {
        $.ajax({
            type: 'DELETE',
            url: nodeApiUrl + 'pointer/',
            data: JSON.stringify({pointerId: pointerId}),
            contentType: 'application/json',
            dataType: 'json',
            success: function(response) {
                pointerElm.remove();
            }
        })
    }

    $('.remove-pointer').on('click', function() {
        bootbox.confirm(
            'Are you sure you want to remove this pointer? This will not ' +
            'remove the project this pointer is linked to.',
            function(result) {
                if (result) {
                    var $this = $(this),
                        pointerId = $this.attr('data-id'),
                        pointerElm = $this.closest('.list-group-item');
                    removePointer(pointerId, pointerElm);
                }
            }
        )
    });

</script>

