<%inherit file="base.mako"/>
<%def name="title()">OAuth Application settings</%def>
<%def name="content()">
<% from website import settings %>
<h2 class="page-header">OAuth application settings</h2>

<div class="row">

    <div class="col-sm-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
                <li><a href="${ web_url_for('oauth_application_config') }">Developer apps</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9 col-md-7">

        % if app_data is not None:
            ## Reuse this template for creation and deletion
                <!-- TODO: Style -->
            <div class="">
                <span class="text-muted">Client ID:</span> <span class="">${app_data["client_id"]}</span><br>
                <span class="text-muted">Client secret:</span> <span class="">${app_data["client_secret"]}</span>
            </div>

            <!-- TODO: Add revoke/ reset buttons -->
        % endif

        <%include file="include/profile/oauth_app_data.mako" />


            <!-- TODO: Rewrite using KO.js and hide the "you have registered" blurb when registered list is empty -->
    </div>
</div>

</%def>

<%def name="javascript_bottom()">
##<script type="text/javascript">
##    ## Store mako variables on window so they are accessible from JS
##    ## modules. Not sure if this is a good idea.
##    window.contextVars = window.contextVars || {};
##    window.contextVars.appDetailUrls = {
##      TODO: Make sure template url is correct
##        crud: '${ api_v2_url_for('users:application-detail', kwargs={'pk': user_id, 'client_id': client_id}) }'
##    };
##</script>
##<script src=${"/static/public/js/profile-settings-page.js" | webpack_asset}></script>
</%def>
