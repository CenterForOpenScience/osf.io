<li id="projects-widget" node_id="${summary['id']}" class="project list-group-item" style="display: list-item;">

    <h3 style="line-height:18px;">
        <span style="display:inline-block">
        <a href="${summary['url']}">${summary['title']}</a>
        % if is_registration:
            | registered: ${registered_date}
        % endif
        </span>
        % if summary['show_logs']:
            <i style="float:right;" id="icon-${summary['id']}" class="icon-plus" onclick="openCloseNode('${summary['id']}');"></i>
        % endif
    </h3>

    <!-- Show abbreviated contributors list -->
    % if summary['show_contributors']:
        <div mod-meta='{
                "tpl": "util/render_users_abbrev.mako",
                "uri": "${summary['api_url']}contributors_abbrev/",
                "kwargs": {
                    "node_url": "${summary['url']}"
                },
                "replace": true
            }'>
        </div>
    % else:
        <div style="padding: 0px 10px 10px 10px;">Contributors unavailable</div>
    % endif

    % if summary['show_logs']:

        <!--Stacked bar to visualize user activity level against total activity level of a project -->
        <!--Length of the stacked bar is normalized over all projects -->
        <div class="user-activity-meter">
            <ul class="meter-wrapper">
                <li class="ua-meter" data-toggle="tooltip" title="${user_full_name} made ${summary['ua_count']} contributions" style="width:${summary['ua']}px;"></li>
                <li class="pa-meter" style="width:${summary['non_ua']}px;"></li>
                <li class="pa-meter-label">${summary['nlogs']} contributions</li>
            </ul>
        </div>

        <script>
            $('.ua-meter').tooltip();
        </script>

        <div class="body hide" id="body-${summary['id']}" style="overflow:hidden;">
            Recent Activity
            <div id="logs-${summary['id']}" class="log-container" data-uri="${summary['url']}log/"></div>
        </div>

    % endif

</li>
