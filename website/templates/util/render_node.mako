% if summary['can_view']:

    <li
            node_id="${summary['id']}"
            node_reference="${summary['id']}:${'node' if summary['primary'] else 'pointer'}"
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
            <span data-bind="getIcon: ${ summary['category'] | sjson, n }"></span>
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

            <!-- Show/Hide recent activity log -->
            % if not summary['archiving']:
            <div class="pull-right">
                % if not summary['primary'] and 'write' in user['permissions'] and not node['is_registration']:
                    <i class="fa fa-times remove-pointer" data-id="${summary['id']}" data-toggle="tooltip" title="Remove link"></i>
                    <i class="fa fa-code-fork" onclick="NodeActions.forkPointer('${summary['id']}', '${summary['primary_id']}');" data-toggle="tooltip" title="Fork this ${summary['node_type']} into ${node['node_type']} ${node['title']}"></i>
                % endif
                <i id="icon-${summary['id']}" class="pointer fa fa-angle-down" onclick="NodeActions.openCloseNode('${summary['id']}');" style="font-weight:bold;"></i>
            </div>
            % endif
        </h4>

        % if summary['show_path'] and summary['node_type'] == 'component':
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
        % if not summary['anonymous']:
            % if summary['nlogs'] > 1:
                <span class="text-muted">${summary['nlogs']} contributions</span>
            % else:
                <span class="text-muted">${summary['nlogs']} contribution</span>
            % endif
        % endif
        % if not summary['archiving']:
            <div class="body hide" id="body-${summary['id']}" style="overflow:hidden;">
            <hr />
            % if summary['is_retracted']:
                <h4>Recent activity information has been withdrawn.</h4>
            % else:
                Recent activity
                <!-- ko stopBinding: true -->
                    <div id="logs-${summary['id']}" class="log-container" data-uri="${summary['api_url']}log/">
                        <dl class="dl-horizontal activity-log" data-bind="foreach: {data: logs, as: 'log'}">
                            <dt><span class="date log-date" data-bind="text: log.date.local, tooltip: {title: log.date.utc}"></span></dt>
                            <dd class="log-content">
                                <span data-bind="if:log.anonymous">
                                    <span data-bind="html: $parent.anonymousUserName"></span>
                                </span>

                                <!-- ko ifnot: log.anonymous -->
                                    <a data-bind="text: log.userFullName, attr: {href: log.userURL}"></a>
                                <!-- /ko -->

                                <!-- ko if: log.hasUser() -->
                                    <!-- log actions are the same as their template name -->
                                    <span data-bind="template: {name: log.action, data: log}"></span>
                                <!-- /ko -->

                                <!-- ko ifnot: log.hasUser() -->
                                    <!-- Log actions are the same as their template name  + no_user -->
                                    <span data-bind="template: {name: log.action + '_no_user', data: log}"></span>
                                <!-- /ko -->
                            </dd>
                        </dl><!-- end foreach logs -->
                    </div>
                <!-- /ko -->
            % endif
        </div>
        % endif
    </li>

% else:
    <li
        node_reference="${summary['id']}:${'node' if summary['primary'] else 'pointer'}"
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
            % if not summary['primary'] and 'write' in user['permissions'] and not node['is_registration']:
                ## Allow deletion of pointers, even if user doesn't know what they are deleting
                <span class="pull-right">
                    <i class="fa fa-times remove-pointer pointer" data-id="${summary['id']}" data-toggle="tooltip" title="Remove link"></i>
                </span>
            % endif
        </p>
    </li>

% endif
