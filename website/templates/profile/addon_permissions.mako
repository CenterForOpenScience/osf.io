% if nodes:
    <div style="margin-right: 20px; margin-left: 20px" id="${addon_short_name}-header">
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

    <script>
        $('.${addon_short_name}-remove-token').on('click', function(event) {
            var nodeId = $(this).attr('node-id');
            bootbox.confirm('Are you sure you want to remove the ${addon_full_name} authorization from this project?', function(confirm) {
                if (confirm) {
                    $.ajax({
                        type: 'DELETE',
                        url: '/api/v1/project/' + nodeId + '/${addon_short_name}/config/',

                        success: function(response) {

                            $("#${addon_short_name}-" + nodeId + "-auth-row").hide();
                            if ($("#${addon_short_name}-auth-table tr:visible").length === 0) {
                                $("#${addon_short_name}-header").hide();
                            }
                        },

                        error: function() {
                            bootbox.alert('An error occurred, the project has not been deauthorized. ' +
                                'If the issue persists, please report it to <a href="mailto:support@osf.io">support@osf.io</a>.');
                        }
                    });
                }
            });
        });
    </script>
% endif