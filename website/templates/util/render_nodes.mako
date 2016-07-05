% if len(nodes):
    <ul data-bind="stopBinding: true" class="list-group m-md ${'sortable' if sortable and 'write' in user['permissions'] else ''}">
        <span id='${pluralized_node_type if pluralized_node_type is not UNDEFINED else 'osfNodeList'}' class="render-nodes-list scripted">
        % for each in nodes:
            <div mod-meta='{
                    "tpl": "util/render_node.mako",
                    "uri": "${each['api_url']}get_summary/",
                    "view_kwargs": {
                        "primary": ${int(each['primary'])},
                        "link_id": "${each['id']}",
                        "uid": "${user_id}",
                        "show_path": ${"true" if show_path else "false"}
                    },
                    "replace": true
                }'></div>
        % endfor
      </span>
    </ul>
    <script>
    % if sortable and 'write' in user['permissions']:
          $(function(){
              $('.sortable').sortable({
                  containment: '#containment',
                  tolerance: 'pointer',
                  items: '#render-node > li',
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
    % elif user.get('is_profile', False):
    <div class="help-block">
      You have no public ${pluralized_node_type}.
        <p>
            Find out how to make your ${pluralized_node_type}
            <a href="https://osf.io/getting-started/#privacy" target="_blank">public</a>.
        </p>
    </div>
% elif profile is not UNDEFINED:  ## On profile page and user has no public projects/components
    <div class="help-block">This user has no public ${pluralized_node_type}.</div>
% else:
    <div class="help-block">No ${pluralized_node_type} to display.</div>
% endif
% if not skipBindings:
    <script src=${"/static/public/js/render-nodes.js" | webpack_asset}></script>
% endif
