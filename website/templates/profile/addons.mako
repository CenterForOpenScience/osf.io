<%inherit file="base.mako"/>
<%def name="title()">Configure Add-on Accounts</%def>

<%def name="stylesheets()">
   ${parent.stylesheets()}
   <link rel="stylesheet" href='/static/css/user-addon-settings.css'>
</%def>

<%def name="content()">
<style>
.addon-icon {
    width: 20px;
    margin-top: -2px;
}
</style>

<% from website import settings %>
<h2 class="page-header">Settings</h2>


<div id="addonSettings" class="row">
    <div class="col-sm-3 affix-parent">
        <%include file="include/profile/settings_navpanel.mako" args="current_page='addons'"/>
    </div>

    <div class="col-sm-9 col-md-7">
        <div id="configureAddons" class="panel panel-default">
          <div class="panel-heading clearfix"><h3 class="panel-title">Configure Add-on Accounts</h3></div>
          <div class="panel-body">
          % for addon in addon_settings:
              % if addon['addon_short_name'] == 'github':
                  <div class="dismissible-alerts hidden" data-bind="css: {'hidden': $root.isDismissed('githubOrgs')}">
                      <div class="alert alert-info">
                          <div>
                              <h4>Having issues with your github organizations repos?</h4>
                              <p>
                                  Please visit <a href="http://help.osf.io/">Re-authorizing github repos</a> to learn more about how this issue can be fixed, or email <a href="mailto:contact@osf.io">contact@osf.io</a> with questions for support.<br>
                              </p>
                          </div>
                          <div>
                              <button type="button" class="btn btn-danger" data-bind="click: $root.dismiss.bind($root, 'githubOrgs')" data-dismiss="alert" aria-label="Close">Dismiss</button>
                              <i>(Once dismissed, the alert will not be shown again)</i>
                          </div>
                      </div>
                  </div>
              % endif
              ${ render_user_settings(addon) }
          % if not loop.last:
          <hr />
          % endif

          % endfor
        </div><!-- end panel-body-->
        </div><!-- end panel -->
    </div><!-- end-col -->
</div><!-- end row -->


</%def>

<%def name="render_user_settings(config)">
    <%
       template = config['user_settings_template']
       tpl = template.render(**config)
    %>
    ${ tpl | n }
</%def>

<%def name="stylesheets()">
  ${parent.stylesheets()}
  % for stylesheet in addons_css:
      <link rel="stylesheet" type="text/css" href="${stylesheet}">
  % endfor
</%def>


<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

   <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'addonEnabledSettings': ${ addon_enabled_settings | sjson, n }});
    </script>
    <script src="${"/static/public/js/profile-settings-addons-page.js" | webpack_asset}"></script>

    ## Webpack bundles
    % for js_asset in addons_js:
      <script src="${js_asset | webpack_asset}"></script>
    % endfor
</%def>
