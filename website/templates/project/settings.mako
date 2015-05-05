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

<div class="row project-page">
    <div class="col-sm-3 affix-parent">
        <div class="panel panel-default" data-spy="affix" data-offset-top="60" data-offset-bottom="268">
            <ul class="nav nav-stacked nav-pills">
                % if 'admin' in user['permissions'] and not node['is_registration']:
                    <li><a href="#configureNodeAnchor">Configure ${node['node_type'].capitalize()}</a></li>
                % endif
                % if 'admin' in user['permissions'] and not node['is_registration']:
                    <li><a href="#configureCommentingAnchor">Configure Commenting</a></li>
                % endif

                % if 'write' in user['permissions'] and not node['is_registration']:
                    <li><a href="#selectAddonsAnchor">Select Add-ons</a></li>

                    % if addon_enabled_settings:
                        <li><a href="#configureAddonsAnchor">Configure Add-ons</a></li>
                    % endif

                    <li><a href="#configureNotificationsAnchor">Configure Notifications</a></li>
                %endif

                % if node['is_registration'] and node['is_public'] and 'admin' in user['permissions']:
                    <li><a href="#retractRegistrationAnchor">Retract Public Registration</a></li>
                % endif
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9">

        % if 'admin' in user['permissions'] and not node['is_registration']:

            <div class="panel panel-default">
                <span id="configureNodeAnchor" class="anchor"></span>

                <div class="panel-heading">
                    <h3 id="configureNode" class="panel-title">Configure ${node['node_type'].capitalize()}</h3>
                </div>
                <div id="nodeCategorySettings" class="panel-body">
                  <h5>
                    Category: <select data-bind="options: categories,
                                                 optionsValue: 'value',
                                                 optionsText: 'label',
                                                 value: selectedCategory"></select>
                  </h5>
                  <p>
                    <button data-bind="css: {disabled: !dirty()}, 
                                       click: updateCategory" 
                            class="btn btn-primary">Change</button>
                    <button data-bind="css: {disabled: !dirty()},
                                       click: cancelUpdateCategory"
                            class="btn btn-default">Cancel</button>                
                  </p>
                  <span data-bind="css: messageClass, html: message"></span>
                </div>
                <hr />
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
                <span id="configureCommentingAnchor" class="anchor"></span>

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


        % if 'write' in user['permissions'] and not node['is_registration']:
        <div class="panel panel-default">
            <span id="selectAddonsAnchor" class="anchor"></span>
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
                <span id="configureAddonsAnchor" class="anchor"></span>

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

        % if not node['is_registration'] and user['has_read_permissions']:
            <div class="panel panel-default">
                <span id="configureNotificationsAnchor" class="anchor"></span>

                <div class="panel-heading">
                    <h3 class="panel-title">Configure Notifications</h3>
                </div>

                <form id="notificationSettings" class="osf-treebeard-minimal">
                    <div id="grid">
    <div class="notifications-loading"> <i class="fa fa-spinner notifications-spin"></i> <p class="m-t-sm fg-load-message"> Loading notification settings...  </p> </div>
                    </div>
                    <div class="help-block" style="padding-left: 15px">
                            <p id="configureNotificationsMessage"></p>
                    </div>
                </form>
            </div>
         % endif

        % if node['is_registration'] and node['is_public'] and 'admin' in user['permissions']:
            <div class="panel panel-osf">
                <span id="retractRegistrationAnchor" class="anchor"></span>

                <div class="panel-heading">
                    <h3 class="panel-title">Retract Public Retraction</h3>
                </div>

                <div class="panel-body">
                    <div class="help-block">
                        Retracting a registration will remove its content from the OSF, but leave basic meta-data
                        behind. The title of a retracted registration and its contributor list will remain, as will
                        justification or explanation of the retraction, should you wish to provide it. Retracted
                        registrations will be marked with a <strong>retracted</strong> tag.
                    </div>
                    %if not node['pending_retraction']:
                        <a class="btn btn-danger" href="${web_url_for('node_registration_retraction_get', pid=node['id'])}">Retract Registration</a>
                    % else:
                        <p><strong>This registration is already pending a retraction.</strong></p>
                    %endif


                </div>

            </div>
        % endif
    </div>

</div>

<%def name="render_node_settings(data)">
    <%
       template_name = data['node_settings_template']
       tpl = data['template_lookup'].get_template(template_name).render(**data)
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
      window.contextVars.nodeCategories = ${json.dumps(categories)};
    </script>

    <script type="text/javascript" src=${"/static/public/js/project-settings-page.js" | webpack_asset}></script>

    % for js_asset in addon_js:
    <script src="${js_asset | webpack_asset}"></script>
    % endfor

</%def>
