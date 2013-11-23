% if user['can_view']:

    <li node_id="${node['id']}" class="project list-group-item list-group-item-node">

        <h4 class="list-group-item-heading">
            <span style="display:inline-block;word-wrap:break-word;width:100%;">
            <a href="${node['url']}">${node['title']}</a>
            % if node['is_registration']:
                | Registered: ${node['registered_date']}
            % endif
            </span>
            <i id="icon-${node['id']}" class="icon-plus pull-right" onclick="NodeActions.openCloseNode('${node['id']}');"></i>
        </h4>
        <div class="list-group-item-text"></div>

        <!-- Show abbreviated contributors list -->
        <div mod-meta='{
                "tpl": "util/render_users_abbrev.mako",
                "uri": "${node['api_url']}contributors_abbrev/",
                "kwargs": {
                    "node_url": "${node['url']}"
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

        <div class="body hide" id="body-${node['id']}" style="overflow:hidden;">
            <hr />
            Recent Activity
            <div id="logs-${node['id']}" class="log-container" data-uri="${node['api_url']}log/">
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
