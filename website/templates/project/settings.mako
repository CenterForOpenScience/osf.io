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
    <!-- Begin left column -->
    <div class="col-sm-3 affix-parent scrollspy">

        % if 'write' in user['permissions']:

            <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="60" data-offset-bottom="263"><!-- Begin sidebar -->
                <ul class="nav nav-stacked nav-pills">

                    % if not node['is_registration']:
                        <li><a href="#configureNodeAnchor">Configure ${node['node_type'].capitalize()}</a></li>



                        % if 'write' in user['permissions']:
                            <li><a href="#selectAddonsAnchor">Select Add-ons</a></li>

                            % if addon_enabled_settings:
                                <li><a href="#configureAddonsAnchor">Configure Add-ons</a></li>
                            % endif

                            <li><a href="#configureNotificationsAnchor">Configure Notifications</a></li>
                        % endif

                        % if 'admin' in user['permissions']:
                            <li><a href="#configureCommentingAnchor">Configure Commenting</a></li>
                        % endif


                    % endif

                    % if node['is_registration']:

                        % if (node['is_public'] or node['embargo_end_date']) and 'admin' in user['permissions']:
                            <li><a href="#retractRegistrationAnchor">Retract Public Registration</a></li>
                        % endif

                    % endif

                </ul>
            </div><!-- End sidebar -->
        % endif

    </div>
    <!-- End left column -->

    <!-- Begin right column -->
    <div class="col-sm-9">

        % if 'write' in user['permissions']:  ## Begin Configure Project

            % if not node['is_registration']:
                <div class="panel panel-default">
                    <span id="configureNodeAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 id="configureNode" class="panel-title">Configure ${node['node_type'].capitalize()}</h3>
                    </div>
                    <div id="nodeCategorySettings" class="panel-body">
                        <h5>
                            Category: <select data-bind="attr.disabled: disabled,
                                                        options: categories,
                                                        optionsValue: 'value',
                                                        optionsText: 'label',
                                                        value: selectedCategory"></select>
                        </h5>
                        <p data-bind="if: !disabled">
                            <button data-bind="css: {disabled: !dirty()},
                                               click: cancelUpdateCategory"
                                    class="btn btn-default">Cancel</button>
                            <button data-bind="css: {disabled: !dirty()},
                                               click: updateCategory"
                                    class="btn btn-primary">Change</button>
                        </p>
                        <span data-bind="css: messageClass, html: message"></span>

                        <span data-bind="if: disabled" class="help-block">
                            A top-level project's category cannot be changed
                        </span>
                    </div>

                    % if 'admin' in user['permissions']:
                        <hr />
                        <div class="panel-body">
                            <div class="help-block">
                                A project cannot be deleted if it has any components within it.
                                To delete a parent project, you must first delete all child components
                                by visiting their settings pages.
                            </div>
                            <button id="deleteNode" class="btn btn-danger btn-delete-node">Delete ${node['node_type']}</button>
                        </div>
                    % endif

                </div>

            % endif

        % endif  ## End Configure Project

        % if 'write' in user['permissions']:  ## Begin Select Addons

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="selectAddonsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
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

                            <button id="settings-submit" class="btn btn-success">
                                Apply
                            </button>
                            <div class="addon-settings-message text-success" style="padding-top: 10px;"></div>

                        </form>

                    </div>
                </div>

                % if addon_enabled_settings:
                    <span id="configureAddonsAnchor" class="anchor"></span>

                    <div id="configureAddons" class="panel panel-default">

                        <div class="panel-heading clearfix">
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
        % endif  ## End Select Addons

        % if user['has_read_permissions']:  ## Begin Configure Notifications

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="configureNotificationsAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
                        <h3 class="panel-title">Configure Notifications</h3>
                    </div>
                    <div class="help-block" style="padding-left: 15px">
                        <p class="text-info">These notification settings only apply to you. They do NOT affect any other contributor on this project.</p>
                    </div>
                    <form id="notificationSettings" class="osf-treebeard-minimal">
                        <div id="grid">
                            <div class="notifications-loading">
                                <i class="fa fa-spinner notifications-spin"></i>
                                <p class="m-t-sm fg-load-message"> Loading notification settings...  </p>
                            </div>
                        </div>
                        <div class="help-block" style="padding-left: 15px">
                            <p id="configureNotificationsMessage"></p>
                        </div>
                    </form>
                </div>

            %endif

        % endif End Configure Notifications



        % if 'admin' in user['permissions']:  ## Begin Configure Commenting

            % if not node['is_registration']:

                <div class="panel panel-default">
                    <span id="configureCommentingAnchor" class="anchor"></span>
                    <div class="panel-heading clearfix">
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

                            <button class="btn btn-success">Save</button>

                            <!-- Flashed Messages -->
                            <div class="help-block">
                                <p id="configureCommentingMessage"></p>
                            </div>
                        </form>

                    </div>

                </div>

            % endif

        % endif  ## End Configure Commenting



        % if 'admin' in user['permissions']:  ## Begin Retract Registration

            % if node['is_registration']:

                % if node['is_public'] or node['embargo_end_date']:

                    <div class="panel panel-default">
                        <span id="retractRegistrationAnchor" class="anchor"></span>

                        <div class="panel-heading clearfix">
                            <h3 class="panel-title">Retract Registration</h3>
                        </div>

                        <div class="panel-body">

                            % if parent_node['exists']:

                                <div class="help-block">
                                  Retracting children components of a registration is not allowed. Should you wish to
                                  retract this component, please retract its parent registration <a href="${web_url_for('node_setting', pid=node['root_id'])}">here</a>.
                                </div>

                            % else:

                                <div class="help-block">
                                    Retracting a registration will remove its content from the OSF, but leave basic metadata
                                    behind. The title of a retracted registration and its contributor list will remain, as will
                                    justification or explanation of the retraction, should you wish to provide it. Retracted
                                    registrations will be marked with a <strong>retracted</strong> tag.
                                </div>

                                %if not node['pending_retraction']:
                                    <a class="btn btn-danger" href="${web_url_for('node_registration_retraction_get', pid=node['id'])}">Retract Registration</a>
                                % else:
                                    <p><strong>This registration is already pending a retraction.</strong></p>
                                %endif

                            % endif


                        </div>
                    </div>

                % endif

            % endif

        % endif  ## End Retract Registration

    </div>
    <!-- End right column -->

</div>

<%def name="render_node_settings(data)">
    <%
       template_name = data['node_settings_template']
       tpl = data['template_lookup'].get_template(template_name).render(**data)
    %>
    ${ tpl | n }
</%def>

% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${ capabilities | n }</script>
% endfor


<%def name="stylesheets()">
    ${parent.stylesheets()}

    <link rel="stylesheet" href="/static/css/pages/project-page.css">
</%def>


<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script>
      window.contextVars = window.contextVars || {};
      window.contextVars.node = window.contextVars.node || {};
      window.contextVars.node.nodeType = ${ node['node_type'] | sjson, n };
      window.contextVars.nodeCategories = ${ categories | sjson, n };
    </script>

    <script type="text/javascript" src=${"/static/public/js/project-settings-page.js" | webpack_asset}></script>

    % for js_asset in addon_js:
    <script src="${js_asset | webpack_asset}"></script>
    % endfor

</%def>
