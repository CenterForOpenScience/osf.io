<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Settings</%def>

##<!-- Show API key settings -->
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "${node["api_url"]}keys/",
##        "replace": true,
##        "kwargs": {
##            "route": "${node["url"]}"
##        }
##    }'></div>

<div class="page-header visible-xs">
  <h2 class="text-300">Settings</h2>
</div>

<div class="row">
    <div class="col-sm-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                % if 'admin' in user['permissions'] and not node['is_registration']:
                    <li><a href="#configureNode">Configure ${node['node_type'].capitalize()}</a></li>
                % endif
                % if 'admin' in user['permissions'] and not node['is_registration']:
                    <li><a href="#configureCommenting">Configure Commenting</a></li>
                % endif

                    <li><a href="#configureNotifications">Configure Notifications</a></li>

                % if 'write' in user['permissions'] and not node['is_registration']:
                    <li><a href="#selectAddons">Select Add-ons</a></li>

                % if addon_enabled_settings:
                    <li><a href="#configureAddons">Configure Add-ons</a></li>
                % endif
                %endif
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9">

        % if 'admin' in user['permissions'] and not node['is_registration']:

            <div class="panel panel-default">

                <div class="panel-heading">
                    <h3 id="configureNode" class="panel-title">Configure ${node['node_type'].capitalize()}</h3>
                </div>
                <div class="panel-body">
                    <div class="help-block">
                        A project cannot be deleted if it has any components within it.
                        To delete a parent project, you must first delete all child components
                        by visiting their settings pages.
                    </div>
                    <button id="deleteNode" class="btn btn-danger btn-delete-node">Delete ${node['node_type']}</button>

                </div>

            </div>

            <div class="panel panel-default">
                <span id="configureCommenting" class="anchor"></span>

                <div class="panel-heading">
                    <h3 class="panel-title">Configure Commenting</h3>
                </div>

                <div class="panel-body">

                    <form class="form" id="commentSettings">

                        <div class="radio">
                            <label>
                                <input type="radio" name="commentLevel" value="private" ${'checked' if comments['level'] == 'private' else ''}>
                                Only contributors can post comments
                            </label>
                        </div>
                        <div class="radio">
                            <label>
                                <input type="radio" name="commentLevel" value="public" ${'checked' if comments['level'] == 'public' else ''}>
                                When the ${node['node_type']} is public, any OSF user can post comments
                            </label>
                        </div>

                        <button class="btn btn-success">Submit</button>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p id="configureCommentingMessage"></p>
                        </div>
                    </form>

                </div>

            </div>

        % endif

        % if not node['is_registration'] and user['has_read_permissions']:
            <div class="panel panel-default">
                <span id="configureNotifications" class="anchor"></span>

                <div class="panel-heading">
                    <h3 class="panel-title">Configure Notifications</h3>
                </div>

                <form id="notificationSettings" class="osf-treebeard-minimal">
                    <div id="grid">
    <div class="notifications-loading"> <i class="icon-spinner notifications-spin"></i> <p class="m-t-sm fg-load-message"> Loading notification settings...  </p> </div>
                    </div>
                    <div class="help-block" style="padding-left: 15px">
                            <p id="configureNotificationsMessage"></p>
                    </div>
                </form>
            </div>
         % endif

        % if 'write' in user['permissions']:
        <div class="panel panel-default">
            <span id="selectAddons"></span>
             <div class="panel-heading">
                 <h3 class="panel-title">Select Add-ons</h3>
             </div>
                <div class="panel-body">
                    <form id="selectAddonsForm">

                        % for category in addon_categories:

                            <%
                                addons = [
                                    addon
                                    for addon in addons_available
                                    if category in addon.categories
                                ]
                            %>

                            % if addons:
                                <h3>${category.capitalize()}</h3>
                                % for addon in addons:
                                    <div>
                                        <label>
                                            <input
                                                type="checkbox"
                                                name="${addon.short_name}"
                                                class="addon-select"
                                                ${'checked' if addon.short_name in addons_enabled else ''}
                                                ${'disabled' if (node['is_registration'] or bool(addon.added_mandatory)) else ''}
                                            />
                                            ${addon.full_name}
                                        </label>
                                    </div>
                                % endfor
                            % endif

                        % endfor

                        <br />

                    % if not node['is_registration']:
                        <button id="settings-submit" class="btn btn-success">
                            Submit
                        </button>
                        <div class="addon-settings-message text-success" style="padding-top: 10px;"></div>
                    % endif

                </form>


                </div>
            </div>

            % if addon_enabled_settings:

                <div id="configureAddons" class="panel panel-default">

                    <div class="panel-heading">
                        <h3 class="panel-title">Configure Add-ons</h3>
                    </div>

                    <div class="panel-body">

                    % for node_settings_dict in addon_enabled_settings or []:
                        ${render_node_settings(node_settings_dict)}

                            % if not loop.last:
                                <hr />
                            % endif

                        % endfor
                    </div>
                </div>

            % endif

        % endif

    </div>

</div>

<%def name="render_node_settings(data)">
    <%
       template_name = "{name}/templates/{name}_node_settings.mako".format(name=data['addon_short_name'])
       tpl = context.lookup.get_template(template_name).render(**data)
    %>
    ${tpl}
</%def>

% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${capabilities}</script>
% endfor

<%def name="javascript_bottom()">
    <% import json %>
    ${parent.javascript_bottom()}
    <script>
      window.contextVars = window.contextVars || {};
      window.contextVars.node = window.contextVars.node || {};
      window.contextVars.node.nodeType = '${node['node_type']}';
    </script>

    <script type="text/javascript" src=${"/static/public/js/project-settings-page.js" | webpack_asset}></script>

    % for js_asset in addon_js:
    <script src="${js_asset | webpack_asset}"></script>
    % endfor

</%def>
