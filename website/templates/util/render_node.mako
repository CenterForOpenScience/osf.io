<%namespace name="contributor_list" file="./contributor_list.mako" />
## TODO: Rename summary to node
<%def name="render_node(summary, show_path)">
## TODO: Don't rely on ID

<div id="render-node">
% if summary['can_view']:
    <div
            node_id="${summary['id']}"
            class="
                project list-group-item list-group-item-node cite-container
                ${'pointer' if not summary['primary'] else ''}
        ">

        <h4 class="list-group-item-heading">
            <span class="component-overflow f-w-lg" style="line-height: 1.5;">
            % if not summary['primary']:
                <i class="fa fa-link" data-toggle="tooltip" title="Linked ${summary['node_type']}"></i>
            % endif

            % if not summary['is_public']:
                <span class="fa fa-lock" data-toggle="tooltip" title="This project is private"></span>
            % endif
                <span class="project-statuses-lg">
                    % if summary['is_pending_registration']:
                        <span class="label label-info"><strong>Pending registration</strong></span> |
                    % elif summary['is_retracted']:
                        <span class="label label-danger"><strong>Withdrawn</strong></span> |
                    % elif summary['is_pending_retraction']:
                        <span class="label label-info"><strong>Pending withdrawal</strong></span> |
                    % elif summary['is_embargoed']:
                        <span class="label label-info"><strong>Embargoed</strong></span> |
                    % elif summary['is_pending_embargo']:
                        <span class="label label-info"><strong>Pending embargo</strong></span> |
                    % endif
                    % if summary['archiving']:
                        <span class="label label-primary"><strong>Archiving</strong></span> |
                    % endif
                </span>
            <span data-bind='getIcon: ${ summary["category"] | sjson, n }'></span>
            % if not summary['archiving']:
                <a href="${summary['url']}">${summary['title']}</a>
            % else:
                <span class="f-w-lg">${summary['title']}</span>
            % endif

            % if summary['is_registration']:
                | Registered: ${summary['registered_date']}
            % elif summary['is_fork']:
                | Forked: ${summary['forked_date']}
            % endif
            </span>

            % if not summary['archiving']:
            <div class="pull-right">
                % if not summary['primary'] and permissions.WRITE in user['permissions'] and not node['is_registration']:
                    <i class="fa fa-times remove-pointer" data-id="${summary['id']}" data-toggle="tooltip" title="Remove link"></i>
                    <i class="fa fa-code-fork" onclick="NodeActions.forkPointer('${summary['id']}', '${summary['primary_id']}');" data-toggle="tooltip" title="Create a fork of ${summary['title']}"></i>
                % endif
                % if summary['primary'] and summary['logged_in'] and summary['is_contributor_or_group_member'] and not summary['is_registration']:
                    <div class="generic-dropdown dropdown pull-right">
                        <button class="btn btn-default dropdown-toggle dropdown-toggle-sm" type="button" data-toggle="dropdown">
                            <span class="fa fa-ellipsis-h"></span>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-right">
                            <li><a tabindex="-1" href="${domain}${summary['id']}/contributors/">Manage Contributors</a></li>
                            <li><a tabindex="-1" href="${domain}${summary['id']}/settings/">Settings</a></li>
                            % if summary['is_admin']:
                            <li>
                                <a tabindex="-1"
                                    data-toggle="modal" data-target="#nodesDelete"
                                    data-bind="click: $root.delete.bind($root, ${summary['childExists'] | sjson, n}, '${summary['node_type']}', ${summary['is_supplemental_project'] | sjson, n},  '${summary['api_url']}')"
                                    type="button">
                                    Delete
                                </a>
                            </li>
                            % endif
                        </ul>
                  </div>
                % endif
            </div>
            % endif
        </h4>

        % if show_path and summary['node_type'] == 'component':
            <div style="padding-bottom: 10px">
                % if summary['parent_is_public']:
                    ${summary['parent_title']}
                % else:
                    <em>-- private project --</em>
                % endif
                 / <b>${summary['title']}</b>
            </div>
        % endif

        <div class="list-group-item-text"></div>

        % if not summary['anonymous']:
        <!-- Show abbreviated contributors list -->
        <div class="project-authors">
            ${contributor_list.render_contributors(contributors=summary['contributors'], others_count=summary['others_count'], node_url=summary['url'])}
        </div>
        % if summary['groups']:
            <div class="project-authors">
                ${summary['groups']}
            </div>
        % endif
        % else:
            <div>Anonymous Contributors</div>
        % endif
        % if summary['description']:
            <span class="high-contrast-link" >${summary['description']}</span>
        % endif
        % if not summary['archiving']:
            <div class="body hide" id="body-${summary['id']}" style="overflow:hidden;">
            <hr />
            % if summary['is_retracted']:
                <h4>Recent activity information has been withdrawn.</h4>
            % else:
                <!-- Recent Activity (Logs) -->
                Recent Activity
                <div id="logFeed-${summary['primary_id'] if not summary['primary'] else summary['id']}">
                    <div class="spinner-loading-wrapper">
                        <div class="ball-scale ball-scale-blue">
                            <div></div>
                        </div>
                         <p class="m-t-sm fg-load-message"> Loading logs...  </p>
                    </div>
                </div>
            % endif
        </div>
        % endif
    </div>

% else:
    <li
        node_id="${summary['id']}"
        class="project list-group-item list-group-item-node">
        <p class="list-group-item-heading f-w-lg">
            %if summary['is_registration']:
                Private Registration
            %elif summary['is_fork']:
                Private Fork
            %elif not summary['primary']:
                Private Link
            %else:
                Private Component
            %endif
            % if not summary['primary'] and permissions.WRITE in user['permissions'] and not node['is_registration']:
                ## Allow deletion of pointers, even if user doesn't know what they are deleting
                <span class="pull-right">
                    <i class="fa fa-times remove-pointer pointer" data-id="${summary['id']}"
                    data-toggle="tooltip" title="Remove link"></i>
                </span>
            % endif
        </p>
    </li>

% endif
</div>
<script type="text/javascript">
    window.contextVars = window.contextVars || {};
    var nodes = window.contextVars.nodes || [];
    nodes.push({
        node : ${summary | sjson, n},
        id: ${summary['primary_id'] if not summary['primary'] and summary['can_view'] else summary['id'] | sjson, n}
    });
    window.contextVars = $.extend(true, {}, window.contextVars, {
        nodes : nodes
    });
</script>
</%def>
