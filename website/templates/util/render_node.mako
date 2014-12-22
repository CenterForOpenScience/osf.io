% if summary['can_view']:

    <li
            node_id="${summary['id']}"
            node_reference="${summary['id']}:${'node' if summary['primary'] else 'pointer'}"
            class="
                project list-group-item list-group-item-node cite-container
                ${'pointer' if not summary['primary'] else ''}
        ">

        <h4 class="list-group-item-heading">
            <span class="component-overflow">
            % if not summary['primary']:
              <i class="icon icon-link" data-toggle="tooltip" title="Linked ${summary['node_type']}"></i>
            % endif

            % if not summary['is_public']:
                <span class="icon icon-lock" data-toggle="tooltip" title="This project is private"></span>
            % endif
            <a href="${summary['url']}">${summary['title']}</a>

            % if summary['is_registration']:
                | Registered: ${summary['registered_date']}
            % endif
            </span>

            <div class="pull-right">
                % if not summary['primary'] and 'admin' in user['permissions']:
                    <i class="icon-remove remove-pointer" data-id="${summary['id']}" data-toggle="tooltip" title="Remove link"></i>
                    <i class="icon-code-fork" onclick="NodeActions.forkPointer('${summary['id']}', '${summary['primary_id']}');" data-toggle="tooltip" title="Fork this ${summary['node_type']} into ${node['node_type']} ${node['title']}"></i>
                % endif
                <i id="icon-${summary['id']}" class="pointer icon-plus" onclick="NodeActions.openCloseNode('${summary['id']}');" data-toggle="tooltip" title="More"></i>
            </div>
        </h4>
        <div class="list-group-item-text"></div>

        % if not summary['anonymous']:
        <!-- Show abbreviated contributors list -->
        <div mod-meta='{
                "tpl": "util/render_users_abbrev.mako",
                "uri": "${summary['api_url']}contributors_abbrev/",
                "kwargs": {
                    "node_url": "${summary['url']}"
                },
                "replace": true
            }'></div>
        % else:
         <div>Anonymous Contributors</div>
        % endif
        <!--Stacked bar to visualize user activity level against total activity level of a project -->
        <!--Length of the stacked bar is normalized over all projects -->
        % if not summary['anonymous']:
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
        <div class="body hide" id="body-${summary['id']}" style="overflow:hidden;">
            <hr />
            Recent Activity
            <div id="logs-${summary['id']}" class="log-container" data-uri="${summary['api_url']}log/">
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
        node_reference="${summary['id']}:${'node' if summary['primary'] else 'pointer'}"
        class="project list-group-item list-group-item-node unavailable">
        <h4 class="list-group-item-heading">
            %if summary['is_registration']:
                Private Registration
            %elif summary['is_fork']:
                Private Fork
            %else:
                Private Component
            %endif
        </h4>
    </li>

% endif
