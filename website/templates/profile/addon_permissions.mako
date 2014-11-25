% if nodes:
    <div class ="table-less" style="margin-right: 20px; margin-left: 20px;" id="${addon_short_name}-header">
        <table class="table table-hover" id="${addon_short_name}-auth-table">
             <thead><th>Authorized Projects:</th><th></th></thead>
            % for node in nodes:
                 <tr id="${addon_short_name}-${node['_id']}-auth-row">
                     <th>
                         <a style="font-weight: normal" href="${node['url']}">
                             % if node['registered']:
                                 [ Registration ]
                             % endif
                             ${node['title']}
                         </a>
                     </th>
                     <th>
                         <a>
                             <i class="icon-remove pull-right text-danger ${addon_short_name}-remove-token" node-id="${node['_id']}" title="Deauthorize Project"></i>
                         </a>
                     </th>
                 </tr>
            % endfor
        </table>
    </div>
    %if len(nodes) > 3:
        <div class="text-center" >
            <i id="${addon_short_name}-more" class="icon-double-angle-down icon-large collapse-button"></i>
            <i style="display: none;" id="${addon_short_name}-less" class="icon-double-angle-up icon-large collapse-button"></i>
        </div>
    %endif
    <script>
        $('.${addon_short_name}-remove-token').on('click', function(event) {
            var nodeId = $(this).attr('node-id');
            bootbox.confirm({
                title: 'Remove addon?',
                message: 'Are you sure you want to remove the ${addon_full_name} authorization from this project?',
                callback: function(confirm) {
                    if(confirm) {
                        $.ajax({
                        type: 'DELETE',
                        url: '/api/v1/project/' + nodeId + '/${addon_short_name}/config/',

                        success: function(response) {

                            $("#${addon_short_name}-" + nodeId + "-auth-row").hide();
                            var numNodes = $("#${addon_short_name}-auth-table tr:visible").length;
                            if (numNodes === 1) {
                                $("#${addon_short_name}-auth-table").hide();
                            }
                            if (numNodes === 4) {
                                $("#${addon_short_name}-more").hide();
                                $("#${addon_short_name}-less").hide();
                            }
                        },

                        error: function() {
                            $.osf.growl('An error occurred, the project has not been deauthorized. ',
                                'If the issue persists, please report it to <a href="mailto:support@osf.io">support@osf.io</a>.');
                        }
                    });
                    }
                }
            });
        });

        $('#${addon_short_name}-more').on('click', function(event) {
            $('#${addon_short_name}-header').removeClass('table-less');
            $('#${addon_short_name}-more').hide();
            $('#${addon_short_name}-less').show();
        });
        $('#${addon_short_name}-less').on('click', function(event) {
            $('#${addon_short_name}-header').addClass('table-less');
            $('#${addon_short_name}-less').hide();
            $('#${addon_short_name}-more').show();
        });

    </script>
% endif
