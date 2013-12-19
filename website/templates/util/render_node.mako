% if summary['can_view']:

    <li node_id="${summary['id']}" class="project list-group-item list-group-item-node cite-container">

        <h4 class="list-group-item-heading">
            <span class="overflow" style="display:inline-block;">
            % if node:
                <a
                  % if node['link']:
                    href="${summary['url']}?key=${node['link']}"
                  %else:
                    href="${summary['url']}"
                  % endif
                        >${summary['title']}</a>
            % else:
                <a href="${summary['url']}">${summary['title']}</a>
            % endif
            % if summary['is_registration']:
                | Registered: ${summary['registered_date']}
            % endif
            </span>
            <i id="icon-${summary['id']}" class="icon-plus pull-right" onclick="NodeActions.openCloseNode('${summary['id']}');"></i>
        </h4>
        <div class="list-group-item-text"></div>

        <!-- Show abbreviated contributors list -->
        <div mod-meta='{
                "tpl": "util/render_users_abbrev.mako",
                "uri": "${summary['api_url']}contributors_abbrev/",
                "kwargs": {
                    "node_url": "${summary['url']}"
                },
                "replace": true
            }'>
        </div>

        <!--Stacked bar to visualize user activity level against total activity level of a project -->
        <!--Length of the stacked bar is normalized over all projects -->
        <div class="user-activity-meter">
            <ul class="meter-wrapper">
                <li class="ua-meter" data-toggle="tooltip" title="${user_full_name} made ${summary['ua_count']} contributions" style="width:${summary['ua']}px;"></li>
                <li class="pa-meter" style="width:${summary['non_ua']}px;"></li>
                <li class="pa-meter-label">${summary['nlogs']} contributions</li>
            </ul>
        </div>

        <div class="body hide" id="body-${summary['id']}" style="overflow:hidden;">
            <hr />
            Recent Activity
            % if node:
                <div id="logs-${summary['id']}" class="log-container"
                      % if node['link']:
                        data-uri="${summary['api_url']}log/?key=${node['link']}"
                      %else:
                        data-uri="${summary['api_url']}log/"
                      % endif
                     >
            % else:
                <div id="logs-${summary['id']}" class="log-container" data-uri="${summary['api_url']}log/">
            % endif
                    <dl class="dl-horizontal activity-log"
                        data-bind="foreach: {data: logs, as: 'log'}">
                        <dt><span class="date log-date" data-bind="text: log.date.local, tooltip: {title: log.date.utc}"></span></dt>
                      <dd class="log-content">
                        <a data-bind="text: log.userFullName || log.apiKey, attr: {href: log.userURL}"></a>
                        <!-- log actions are the same as their template name -->
                        <span data-bind="template: {name: log.action, data: log}"></span>
                      </dd>
                    </dl><!-- end foreach logs -->
                </div>
         </div>

    </li>

% else:

    <li class="project list-group-item list-group-item-node unavailable">
        <h4 class="list-group-item-heading">
            Private Component
        </h4>
    </li>

% endif
