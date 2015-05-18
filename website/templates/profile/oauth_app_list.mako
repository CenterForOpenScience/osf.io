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
                <li><a href="#">Developer apps</a> </li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9 col-md-7">
        <a href="#" role="button" class="btn btn-default pull-right"><i class="fa fa-plus"></i> Register new application</a>

        <p>You have registered the following applications that can connect to the OSF:</p>

        <table class="table table-condensed">
            <tr>
                <th>Application</th>
                <th>
                    <span class="pull-right">
                        Delete <span class="glyphicon glyphicon-info-sign" aria-hidden="true"
                                     title="Deleting this API key will de-authorize any external applications that use it to connect to the OSF. This cannot be reversed!"></span>
                    </span>
                </th>
            </tr>
            %for reg_app in known_apps:
                <tr>
                    <td>
                        <a href="${web_url_for('oauth_application_detail', cid=reg_app['id'])}">${reg_app['name']}</a>
                        <p>Client ID: <span class="text-muted">${reg_app['id']} </span></p>
                    </td>
                    <td>
                        <!-- TODO- how does link know WHAT to delete? -->
                        <a href="#" data-bind="click: delete"><i class="fa fa-times text-danger pull-right"></i></a>
                    </td>
                </tr>
            %endfor
        </table>

        <!-- TODO: Rewrite using KO.js and hide the "you have registered" blurb when registered list is empty -->

    </div>

</div>

</%def>


<%def name="javascript_bottom()">
##<script type="text/javascript">
##    ## Store mako variables on window so they are accessible from JS
##    ## modules. Not sure if this is a good idea.
##    window.contextVars = window.contextVars || {};
##    window.contextVars.appListUrls = {
##        // TODO: Insert user id and possibly application ID into these urls, eg  api_v2_url_for("users:application-detail", kwargs={'pk':'abs', 'client_id':'asdf'})
##        cr: '${ api_v2_url_for('users:application-list', kwargs={'pk': user_id}) }',
##        //rud: '${ api_v2_url_for('users:application-detail') }'
##    };
##</script>
<script src=${"/static/public/js/profile-settings-applications.js" | webpack_asset}></script>
</%def>
