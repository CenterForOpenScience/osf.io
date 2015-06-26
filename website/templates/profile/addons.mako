<%inherit file="base.mako"/>
<%def name="title()">Configure External Accounts </%def>
<%def name="content()">
<style>
.addon-icon {
    width: 20px;
}
</style>

<% from website import settings %>
<h2 class="page-header">Configure External Accounts</h2>

<div class="row">

    <div class="col-sm-3">

        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="#">Configure External Accounts</a></li>
                <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9 col-md-7">
      <div id="configureAddons" class="panel panel-default">
        <div class="panel-heading"><h3 class="panel-title">Configure External Accounts</h3></div>
        <div class="panel-body">
          % for addon in addon_settings:
            ${render_user_settings(addon) }
          % if not loop.last:
          <hr />
          % endif
          
          % endfor
        </div>
      </div>
    </div>    
</div>


% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${capabilities}</script>
% endfor

</%def>

<%def name="render_user_settings(config)">
    <%
       template = config['user_settings_template']
       tpl = template.render(**config)
    %>
    ${tpl}
</%def>

<%def name="stylesheets()">
  ${parent.stylesheets()}
  % for stylesheet in addons_css:
      <link rel="stylesheet" type="text/css" href="${stylesheet}">
  % endfor
</%def>


<%def name="javascript_bottom()">
    <% import json %>
    ${parent.javascript_bottom()}
    
   <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'addonEnabledSettings': ${json.dumps(addon_enabled_settings)}});
    </script>
    <script src="${"/static/public/js/profile-settings-addons-page.js" | webpack_asset}"></script>

    ## Webpack bundles
    % for js_asset in addons_js:
      <script src="${js_asset | webpack_asset}"></script>
    % endfor
</%def>
