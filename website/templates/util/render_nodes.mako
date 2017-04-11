<%namespace name="render_node" file="./render_node.mako" />

<%def name="render_nodes(nodes, sortable, user, pluralized_node_type, show_path, include_js=True)">

    % if len(nodes):
        <ul data-bind="stopBinding: true" class="list-group m-md ${'sortable' if sortable and 'write' in user['permissions'] else ''}">
            ## TODO: Add .scripted when JS is hooked up
            <span id='${pluralized_node_type if pluralized_node_type is not UNDEFINED else 'osfNodeList'}' class="render-nodes-list">
                % for each in nodes:
                    ${ render_node.render_node(each, show_path=show_path) }
                % endfor
            </span>
        </ul>
        % if sortable and 'write' in user['permissions']:
        <script>
            $(function(){
                $('.sortable').sortable({
                    containment: '#containment',
                    tolerance: 'pointer',
                    items: '#render-node > li',
                    stop: function(event, ui){
                        var sortListElm = this;
                        var idList = $(sortListElm).sortable(
                            'toArray',
                            {attribute: 'node_id'}
                        );
                        NodeActions.reorderChildren(idList, sortListElm);
                    }
                });
            });
        </script>
        % endif
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

    % if include_js:
        <script src=${"/static/public/js/render-nodes.js" | webpack_asset}></script>
    % endif
</%def>
