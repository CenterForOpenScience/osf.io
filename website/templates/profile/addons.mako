<%inherit file="base.mako"/>
<%def name="title()">Configure Add-ons</%def>
<%def name="content()">
<% from website import settings %>
<h2 class="page-header">Configure Add-ons</h2>

<div class="row affix-menu">
    <div class="col-sm-3 affix-parent">
        <div class="panel panel-default profile-panel profile" data-spy="affix" data-offset-top="100" data-offset-bottom="268">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="#">Configure Add-ons</a></li>
                <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9 col-md-7">

        <div id="selectAddons" class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Select Add-ons</h3></div>
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
                                            ${'checked' if (addon.short_name in addons_enabled) else ''}
                                        />
                                        ${addon.full_name}
                                    </label>
                                </div>
                            % endfor
                        % endif

                    % endfor

                    <br />

                    <button id="settings-submit" class="btn btn-success">
                        Submit
                    </button>

                </form>

            </div>
        </div>
        % if addon_enabled_settings:
            <div id="configureAddons" class="panel panel-default">
                <div class="panel-heading"><h3 class="panel-title">Configure Add-ons</h3></div>
                <div class="panel-body">

                    % for name in addon_enabled_settings:
                        ${render_user_settings(user_addons_enabled[name])}
                        % if not loop.last:
                            <hr />
                        % endif

                    % endfor
                </div>
            </div>
            % endif
    </div>

</div>


% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${capabilities}</script>
% endfor

</%def>

<%def name="render_user_settings(data)">
    <%
       template_name = data['user_settings_template']
       tpl = data['template_lookup'].get_template(template_name).render(**data)
    %>
    ${tpl}
</%def>


<%def name="javascript_bottom()">
    <% import json %>
    ${parent.javascript_bottom()}

   <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'addonEnabledSettings': ${json.dumps(addon_enabled_settings)}});
    </script>
    <script src="${"/static/public/js/profile-settings-addons-page.js" | webpack_asset}"></script>
    ## Webpack bundles
    % for js_asset in addon_js:
      <script src="${js_asset | webpack_asset}"></script>
    % endfor
</%def>
