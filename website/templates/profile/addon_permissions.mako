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
        AddonPermissionsTable.init("${addon_short_name}", "${addon_full_name}");
    </script>
% endif
