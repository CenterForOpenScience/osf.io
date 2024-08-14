<%namespace name="render_node" file="./render_node.mako" />

<%def name="render_nodes(user, pluralized_node_type, show_path, include_js=True)">

    <!-- ko if: nodes().length > 0 -->
        <ul data-bind="css: {'list-group': true, 'm-md': true, 'sortable': sortable && hasPermission('write')}">
            ## TODO: Add .scripted when JS is hooked up
            <span id='${pluralized_node_type if pluralized_node_type is not UNDEFINED else 'osfNodeList'}' class="render-nodes-list">
                <!-- ko foreach: nodes -->
                    ${ render_node.render_node(show_path=show_path) }
                <!-- /ko -->
                <%include file="../project/nodes_delete.mako"/>
            </span>
        </ul>
        <!-- ko if: sortable && hasPermission('write') && !node.is_registration -->
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
        <!-- /ko -->
    <!-- /ko -->
    <!-- ko if: nodes().length === 0 && user().isProfile -->
        <div class="help-block">
        You have no public ${pluralized_node_type}.
            <p>
                Find out how to make your ${pluralized_node_type}
                <a href="https://rdm.nii.ac.jp/getting-started/#privacy" target="_blank">public</a>.
            </p>
        </div>
    <!-- /ko -->
    <!-- ko if: nodes().length === 0 && !user().isProfile && profile() !== undefined -->
        <div class="help-block">This user has no public ${pluralized_node_type}.</div>
    <!-- /ko -->
    <!-- ko if: nodes().length === 0 && !user().isProfile && profile() === undefined -->
        <div class="help-block">No ${pluralized_node_type} to display.</div>
    <!-- /ko -->
</%def>