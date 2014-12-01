% if summary['can_view']:
    <%
        current_node = summary['node']
        %>
    <li
            node_id="${current_node['link_id']}"
            node_reference="${current_node['link_id']}:${'node' if current_node['primary'] else 'pointer'}"
            class="
                project list-group-item list-group-item-node cite-container
                ${'pointer' if not current_node['primary'] else ''}
        ">

        <h4 class="list-group-item-heading">
            <span class="overflow" style="display:inline-block;">
            % if not current_node['primary']:
              <i class="icon icon-link" data-toggle="tooltip" title="Linked ${current_node['node_type']}"></i>
            % endif

            % if not current_node['is_public']:
                <span class="icon icon-lock" data-toggle="tooltip" title="This project is private"></span>
            % endif

            % if sortable == 'profile-page' and summary['parent_node']['title']:
                % if summary['parent_node']['is_public']:
                    <a href="${summary['parent_node']['url']}">${summary['parent_node']['title']}</a> /
                % else:
                    <i>-- private project --</i> /
                % endif
            % endif
            <a href="${current_node['url']}">${current_node['title']}</a>

            % if current_node['is_registration']:
                | Registered: ${current_node['registered_date']}
            % endif
            </span>

            <div class="pull-right">
                % if not current_node['primary'] and 'admin' in user['permissions']:
                    <i class="icon-remove remove-pointer" data-id="${current_node['link_id']}" data-toggle="tooltip" title="Remove link"></i>
                    <i class="icon-code-fork" onclick="NodeActions.forkPointer('${current_node['link_id']}', '${current_node['primary_id']}');" data-toggle="tooltip" title="Fork this ${current_node['node_type']} into ${node['node_type']} ${node['title']}"></i>
                % endif
                <i id="icon-${current_node['link_id']}" class="pointer icon-plus" onclick="NodeActions.openCloseNode('${current_node['link_id']}');" data-toggle="tooltip" title="More"></i>
            </div>
        </h4>
        <div class="list-group-item-text"></div>

        % if not current_node['anonymous']:
        <!-- Show abbreviated contributors list -->
        <div mod-meta='{
                "tpl": "util/render_users_abbrev.mako",
                "uri": "${current_node['api_url']}contributors_abbrev/",
                "kwargs": {
                    "node_url": "${current_node['url']}"
                },
                "replace": true
            }'></div>
        % else:
         <div>Anonymous Contributors</div>
        % endif
        <!--Stacked bar to visualize user activity level against total activity level of a project -->
        <!--Length of the stacked bar is normalized over all projects -->
        % if not current_node['anonymous']:
            <div class="progress progress-user-activity">
                % if summary['ua']:
                    <div class="progress-bar progress-bar-success ${'last' if not summary['non_ua'] else ''}" style="width: ${summary['ua']}%"  data-toggle="tooltip" title="${user_full_name} made ${summary['ua_count']} contributions"></div>
                % endif
                % if summary['non_ua']:
                    <div class="progress-bar progress-bar-info last" style="width: ${summary['non_ua']}%"></div>
                % endif
            </div>
            <span class="text-muted">${summary['nlogs']} contributions</span>
        % endif
        <div class="body hide" id="body-${current_node['link_id']}" style="overflow:hidden;">
            <hr />
            Recent Activity
            <div id="logs-${current_node['link_id']}" class="log-container" data-uri="${current_node['api_url']}log/">
                <dl class="dl-horizontal activity-log" data-bind="foreach: {data: logs, as: 'log'}">
                    <dt><span class="date log-date" data-bind="text: log.date.local, tooltip: {title: log.date.utc}"></span></dt>
                    <dd class="log-content">
                        <span data-bind="if:log.anonymous">
                            <span><em>A user</em></span>
                        </span>
                        <span data-bind="ifnot:log.anonymous">
                            <a data-bind="text: log.userFullName || log.apiKey, attr: {href: log.userURL}"></a>
                        </span>
                        <!-- log actions are the same as their template name -->
                        <span data-bind="template: {name: log.action, data: log}"></span>
                        </dd>
                </dl><!-- end foreach logs -->
            </div>
         </div>

    </li>

% else:
    <li
        node_reference="${current_node['link_id']}:${'node' if current_node['primary'] else 'pointer'}"
        class="project list-group-item list-group-item-node unavailable">
        <h4 class="list-group-item-heading">
            %if current_node['is_registration']:
                Private Registration
            %elif current_node['is_fork']:
                Private Fork
            %else:
                Private Component
            %endif
        </h4>
    </li>

% endif
