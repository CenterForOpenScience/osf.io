% if nodes:
    <div class="m-h-lg addon-auth-table" id="${addon_short_name}-header">
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

    <script>
        ## Globals are not available to included templates
        <% from website.util.sanitize import safe_json as sjson %>
        window.contextVars = $.extend(true, {}, window.contextVars, {
            addonsWithNodes: {
                ${ addon_short_name | sjson, n }: {
                    shortName: ${ addon_short_name | sjson, n },
                    fullName: ${ addon_full_name | sjson, n }
                }
            }
        });
    </script>
% endif
