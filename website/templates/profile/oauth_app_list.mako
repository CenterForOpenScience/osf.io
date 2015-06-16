<%inherit file="base.mako"/>
<%def name="title()">OAuth Application settings</%def>
<%def name="content()">
<h2 class="page-header">OAuth application settings</h2>

<div class="row">

    <div class="col-sm-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
                %if dev_mode:
                    <li><a href="#">Developer apps</a> </li>
                %endif
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9 col-md-7">
        <a href="${web_url_for('oauth_application_register')}" role="button" class="btn btn-default pull-right"><i class="fa fa-plus"></i> Register new application</a>
        <div id="app-list">

            <p data-bind="visible: (content().length == 0)">You have not registered any applications that can connect to the OSF.</p>
            <div id="if-apps" data-bind="visible: (content().length > 0)">
                <p>You have registered the following applications that can connect to the OSF:</p>

                <table class="table table-condensed">
                    <thead>
                    <tr>
                        <th>Application</th>
                        <th>
                            <span class="pull-right">
                                Delete <span class="glyphicon glyphicon-info-sign" aria-hidden="true"
                                             title="De-registering this application cannot be reversed!"></span>
                            </span>
                        </th>
                    </tr>
                    </thead>
                    <tbody data-bind="foreach: content">
                        <tr>
                            <td>
                                <a href="#" data-bind="attr: {href: detailUrl  }"><span data-bind="text: name"></span></a>
                                <p>Client ID: <span class="text-muted" data-bind="text: clientId"></span></p>
                            </td>
                            <td>
                                <a href="#" data-bind="click: $root.deleteApplication"><i class="fa fa-times text-danger pull-right"></i></a>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

</div>
</%def>


<%def name="javascript_bottom()">

<script type="text/javascript">
    ## Store mako variables on window so they are accessible from JS
    ## modules. Not sure if this is a good idea.
    window.contextVars = window.contextVars || {};
    window.contextVars.urls = {
        dataUrl: ${app_list_url}
    };
</script>
<script src=${"/static/public/js/profile-settings-applications-list-page.js" | webpack_asset}></script>
</%def>
