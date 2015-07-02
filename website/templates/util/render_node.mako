% if summary['can_view']:

    <li
            node_id="${summary['id']}"
            node_reference="${summary['id']}:${'node' if summary['primary'] else 'pointer'}"
            class="
                project list-group-item list-group-item-node cite-container
                ${'pointer' if not summary['primary'] else ''}
        ">

        <h4 class="list-group-item-heading">
            <span class="component-overflow" style="line-height: 1.5;">
            % if not summary['primary']:
              <i class="fa fa-link" data-toggle="tooltip" title="Linked ${summary['node_type']}"></i>
            % endif

            % if not summary['is_public']:
                <span class="fa fa-lock" data-toggle="tooltip" title="This project is private"></span>
            % endif
                <span class="project-statuses-lg">
                  % if summary['is_retracted']:
                  <span class="label label-danger"><strong>Retracted</strong></span> |
                  % elif summary['pending_retraction']:
                  <span class="label label-info"><strong>Pending Retraction</strong></span> |
                  % elif summary['embargo_end_date']:
                  <span class="label label-info"><strong>Embargoed</strong></span> |
                  % elif summary['pending_embargo']:
                  <span class="label label-info"><strong>Pending Embargo</strong></span> |
                  % endif
                  % if summary['archiving']:
                  <span class="label label-primary"><strong>Archiving</strong></span> |
                  % endif
                </span>
            <span data-bind="getIcon: '${summary['category']}'"></span>
            % if not summary['archiving']:
                <a href="${summary['url']}">${summary['title']}</a>
            % endif
            % if summary['archiving']:
                <span>${summary['title']}</span>
            % endif


            % if summary['is_registration']:
                | Registered: ${summary['registered_date']}
            % endif
            </span>

            <!-- Show/Hide recent activity log -->
            % if not summary['archiving']:
            <div class="pull-right">
                % if not summary['primary'] and 'admin' in user['permissions']:
                    <i class="fa fa-times remove-pointer" data-id="${summary['id']}" data-toggle="tooltip" title="Remove link"></i>
                    <i class="fa fa-code-fork" onclick="NodeActions.forkPointer('${summary['id']}', '${summary['primary_id']}');" data-toggle="tooltip" title="Fork this ${summary['node_type']} into ${node['node_type']} ${node['title']}"></i>
                % endif
                <i id="icon-${summary['id']}" class="pointer fa fa-plus" onclick="NodeActions.openCloseNode('${summary['id']}');" data-toggle="tooltip" title="More"></i>
            </div>
            % endif
        </h4>

        % if summary['show_path'] and summary['node_type'] == 'component':
            <div style="padding-bottom: 10px">
                ${summary['parent_title'] if summary['parent_is_public'] else "<em>-- private project --</em>"} / <b>${summary['title']}</b>
            </div>
        % endif

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
        % if not summary['archiving']:
        <div class="body hide" id="body-${summary['id']}" style="overflow:hidden;">
            <hr />
            Recent Activity
            <!-- ko stopBinding: true -->
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
            <!-- /ko -->
         </div>
        % endif
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
            %elif not summary['primary']:
                Private Link
            %else:
                Private Component
            %endif
        </h4>
    </li>

% endif
