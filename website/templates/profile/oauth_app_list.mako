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
        <a href="${web_url_for('oauth_application_register')}" role="button" class="btn btn-default pull-right"><i class="fa fa-plus"></i> Register new application</a>


        <div id="app-list">

            <!-- TODO: Hidden data bindings not firing properly? Rewrite so it also hides the table view entirely -->
            <p data-bind="hidden: !(applicationList.length > 0)">You have registered the following applications that can connect to the OSF:</p>
            <p data-bind="hidden: (applicationsList.length > 0)">You have not registered any applications that can connect to the OSF.</p>

            <table class="table table-condensed">
                <thead>
                <tr>
                    <th>Application</th>
                    <th>
                        <span class="pull-right">
                            Delete <span class="glyphicon glyphicon-info-sign" aria-hidden="true"
                                         title="Deleting this API key will de-authorize any external applications that use it to connect to the OSF. This cannot be reversed!"></span>
                        </span>
                    </th>
                </tr>
                </thead>
                <tbody data-bind="foreach: applicationList">
                <tr><!-- TODO: Write KO to fetch from API -->
                    <td>
                        <!-- TODO: Write delete method that uses an internal URL concatenation method + AJAX delete request -->
                        <a href="#" data-bind="attr: {href: $root.getDetailUrl(client_id)  }"><span data-bind="text: name"></span></a>
                        <p>Client ID: <span class="text-muted" data-bind="text: client_id"></span></p>
                    </td>
                    <td>
                        <!-- TODO- how does link know WHAT to delete? -->
                        <a href="#" data-bind="click: $root.deleteApplication"><i class="fa fa-times text-danger pull-right"></i></a>
                    </td>
                </tr>
                </tbody>
            </table>
        </div>
    </div>

</div>

</%def>


<%def name="javascript_bottom()">
<script type="text/javascript">
    ## Store mako variables on window so they are accessible from JS
    ## modules. Not sure if this is a good idea.
    window.contextVars = window.contextVars || {};
    window.contextVars.appListUrls = {
        // TODO: Insert user id and possibly application ID into these urls, eg  api_v2_url_for("users:application-detail", kwargs={'pk':'abs', 'client_id':'asdf'})
        crud: '${ api_v2_url_for("users:application-list", kwargs={"pk": user_id}) }',
        baseDetailUrl: '/settings/applications/', // Base URL for web detail pages: concatenate client_id to get specific detail page. TODO: Hardcoded URL
        baseApiDetailUrl:  "/api/v2/users/" + "${user_id}" + "/applications/"  // Base URL for API detail calls (used for updates and deletes. TODO: Hardcoded URL
    };
</script>
<script src=${"/static/public/js/profile-settings-applications-list-page.js" | webpack_asset}></script>
</%def>
