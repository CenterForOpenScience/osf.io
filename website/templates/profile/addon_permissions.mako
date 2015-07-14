% if nodes:
    <div style="margin-right: 20px; margin-left: 20px;" id="${addon_short_name}-header">
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
                        % if not node['registered']:
                            <a>
                                <i class="fa fa fa-times pull-right text-danger ${addon_short_name}-remove-token"
                                   api-url="${node['api_url']}" node-id="${node['_id']}" title="Deauthorize Project"></i>
                            </a>
                        % endif
                    </th>
                </tr>
            % endfor
        </table>
    </div>
    %if len(nodes) > 3:
        <div class="text-center" >
            <i id="${addon_short_name}-more" class="fa fa-angle-double-down fa-lg collapse-button"></i>
            <i style="display: none;" id="${addon_short_name}-less" class="fa fa-angle-double-up fa-lg collapse-button"></i>
        </div>
    %endif
    <script>
        window.contextVars = $.extend(true, {}, window.contextVars, {
            addonsWithNodes: {
                '${addon_short_name}': {
                    shortName: '${addon_short_name}',
                    fullName: '${addon_full_name}'
                }
            }
        });
    </script>
% endif
