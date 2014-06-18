% if nodes:
    <div style="margin-right: 20px; margin-left: 20px" id = "${addon_short_name}-header">
        <table class="table table-hove" id="${addon_short_name}-auth-table">
             <thead>Authorized Projects:</thead>

            % for node in nodes:
                 <tr id="${addon_short_name}-${node['_id']}-auth-row">
                    <th><a style="font-weight: normal" href="${node['url']}">${node['title']}</a></th>
                     <th><a><i class="icon-remove pull-right text-danger ${addon_short_name}-remove-token" title="Deauthorize Project"></i></a></th>
                 </tr>
            % endfor
        </table>
    </div>

    <script>
        $('.${addon_short_name}-remove-token').on('click', function(event) {
            var $elm = $(event.target);
            bootbox.confirm('Are you sure you want to remove the ${addon_full_name} authorization from this project?', function(confirm) {
                if (confirm) {
                    $.ajax({
                        type: 'DELETE',
                        url: '/api/v1/project/${node['_id']}/${addon_short_name}/config/',
                        success: function(response) {

                            $("#${addon_short_name}-${node['_id']}-auth-row").hide();
                            if ($("#${addon_short_name}-auth-table tr:visible").length === 0) {
                                $("#${addon_short_name}-header").hide();
                            }
                        },

                        error: function(response) {

                            bootbox.alert('There was a problem, the project has not been deauthorized.');
                        }
                    });
                }
            });
        });
    </script>
% endif