<%namespace name="contributor_list" file="./contributor_list.mako" />
## TODO: Rename summary to node
<%def name="render_node(show_path)">
## TODO: Don't rely on ID
<!-- ${_("component")} -->
<div id="render-node">
<!-- ko if: node.can_view -->
    <li data-bind="attr: { 'node_id': node.id }, css: { project: true, 'list-group-item': true, 'list-group-item-node': true, 'cite-container': true, pointer: node.primary }">
        <h4 class="list-group-item-heading">
            <span class="component-overflow f-w-lg" style="line-height: 1.5;">
                <!-- ko if: !node.primary -->
                <i class="fa fa-link" data-toggle="tooltip" data-bind="attr: { title: localizedNodeType }"></i>
                <!-- /ko -->

                <!-- ko if: !node.is_public -->
                    <span class="fa fa-lock" data-toggle="tooltip" title='${_("This project is private")}'></span>
                <!-- /ko -->
                    <span class="project-statuses-lg">
                        <!-- ko if: node.is_pending_registration -->
                        <span class="label label-info"><strong>Pending registration</strong></span> |
                        <!-- /ko -->

                        <!-- ko if: node.is_retracted -->
                        <span class="label label-danger"><strong>Withdrawn</strong></span> |
                        <!-- /ko -->

                        <!-- ko if: node.is_pending_retraction -->
                        <span class="label label-info"><strong>Pending withdrawal</strong></span> |
                        <!-- /ko -->

                        <!-- ko if: node.is_embargoed -->
                        <span class="label label-info"><strong>Embargoed</strong></span> |
                        <!-- /ko -->

                        <!-- ko if: node.is_pending_embargo -->
                        <span class="label label-info"><strong>Pending embargo</strong></span> |
                        <!-- /ko -->

                        <!-- ko if: node.archiving -->
                        <span class="label label-primary"><strong>Archiving</strong></span> |
                        <!-- /ko -->
                    </span>
                <span data-bind="getIcon: node.category"></span>
                <!-- ko ifnot: node.archiving -->
                <a data-bind="attr: { href: node.url }, text: node.title"></a>
                <!-- /ko -->
                <!-- ko if: node.archiving -->
                <span class="f-w-lg" data-bind="text: node.title"></span>
                <!-- /ko -->

                <!-- ko if: node.is_registration -->
                | Registered: <span data-bind="text: node.registered_date"></span>
                <!-- /ko -->
                <!-- ko if: node.is_fork -->
                | Forked: <span data-bind="text: node.forked_date"></span>
                <!-- /ko -->
            </span>

            <!-- ko ifnot: node.archiving -->
            <div class="pull-right">
                <!-- ko if: !node.primary && $parent.hasPermission('write') && !node.is_registration -->
                <i class="fa fa-times remove-pointer"
                data-bind="attr: { 'data-id': node.id }, 
                            tooltip: { title: _('Remove link') }">
                </i>
                <i class="fa fa-code-fork" 
                data-bind="click: function() { NodeActions.forkPointer(node.id, node.primary_id); }, 
                            tooltip: { title: _('Create a fork of %(summaryTitle)s', {summaryTitle: node.title}) }">
                </i>
                <!-- /ko -->
                
                <!-- ko if: node.primary && node.logged_in && node.is_contributor_or_group_member && !node.is_registration -->
                <div class="generic-dropdown dropdown pull-right">
                    <button class="btn btn-default dropdown-toggle dropdown-toggle-sm" type="button" data-toggle="dropdown">
                        <span class="fa fa-ellipsis-h"></span>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-right">
                        <li>
                            <a tabindex="-1" 
                            data-bind="attr: { href: domain + node.id + '/contributors/' }, 
                                        text: _('Manage Contributors')">
                            </a>
                        </li>
                        <li>
                            <a tabindex="-1" 
                            data-bind="attr: { href: domain + node.id + '/settings/' }, 
                                        text: _('Settings')">
                            </a>
                        </li>
                        <!-- ko if: node.is_admin -->
                        <li>
                            <a tabindex="-1" 
                            data-toggle="modal" data-target="#nodesDelete"
                            data-bind="click: function() { $root.delete(node.childExists, node.node_type, node.is_supplemental_project, node.api_url); }, 
                                        text: _('Delete')">
                            </a>
                        </li>
                        <!-- /ko -->
                    </ul>
                </div>
                <!-- /ko -->
            </div>
            <!-- /ko -->

        </h4>

        <!-- ko if: node.show_path && node.node_type == 'component' -->
            <div style="padding-bottom: 10px">
                <!-- ko if: node.parent_is_public -->
                <span data-bind="text: node.parent_title"></span>
                <!-- /ko -->
                <!-- ko ifnot: node.parent_is_public -->
                <em>-- private project --</em>
                <!-- /ko -->
                / <b data-bind="text: node.title"></b>
            </div>
        <!-- /ko -->

        <div class="list-group-item-text"></div>

        <!-- ko ifnot: node.anonymous -->
            <!-- Show abbreviated contributors list -->
            <!-- ko with: contributors -->
            <div class="project-authors">
                ${contributor_list.render_contributors()}
            </div>
            <!-- /ko -->
            <!-- ko if: node.groups -->
                <div class="project-authors">
                    <span data-bind="text: node.groups"></span>
                </div>
            <!-- /ko -->
        <!-- /ko -->
        <!-- ko if: node.anonymous -->
            <div>Anonymous Contributors</div>
        <!-- /ko -->
        <!-- ko if: node.description -->
            <span class="text-muted" data-bind="text: node.description"></span>
        <!-- /ko -->
        <!-- ko if: node.archiving -->
        <div class="body hide" data-bind="attr: {id: 'body-' + node.id}" style="overflow:hidden;">
            <hr />
            <!-- ko if: node.is_retracted -->
                <h4>Recent activity information has been withdrawn.</h4>
            <!-- /ko -->
            <!-- ko ifnot: node.is_retracted -->
                <!-- Recent Activity (Logs) -->
                Recent Activity
                <div data-bind="attr: { id: 'logFeed-' + (node.primary ? node.id : node.primary_id) }">
                    <div class="spinner-loading-wrapper">
                        <div class="ball-scale ball-scale-blue">
                            <div></div>
                        </div>
                         <p class="m-t-sm fg-load-message"> Loading logs...  </p>
                    </div>
                </div>
            <!-- /ko -->
        </div>
        <!-- /ko -->
    </li>
<!-- /ko -->
<!-- ko ifnot: node.can_view -->
    <li data-bind="attr: { 'node_id': node.id }"
        class="project list-group-item list-group-item-node">
        <p class="list-group-item-heading f-w-lg"
            data-bind="text: displayText">
            <!-- ko if: !node.primary && $parent.hasPermission('write') && !node.is_registration -->
                <span class="pull-right">
                    <i class="fa fa-times remove-pointer pointer" data-bind="attr: { 'data-id': node.id }"
                    data-toggle="tooltip" title="Remove link"></i>
                </span>
            <!-- /ko -->
        </p>
    </li>
<!-- /ko -->
</div>
</%def>