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
        <form role="form" method="post" action="${ web_url_for('oauth_application_register') }">
            <!-- TODO: Write AJAX or KO endpoint for submission -->
            <div class="form-group">
                <label>Application name</label>
                <input class="form-control" type="text" name="appName">
            </div>

            <div class="form-group">
                <label>Project homepage URL</label>
                <input class="form-control" type="text" name="appHomeURL">
            </div>

            <div class="form-group">
                <label>Application description</label>
                <textarea class="form-control" placeholder="Application description is optional" name="appDesc"></textarea>
            </div>

            <div class="form-group">
                <label>Authorization callback URL</label>
                <input type="text" class="form-control" placeholder="Is this field necessary for the OSF API?" name="appCallbackURL">
            </div>


            <div class="padded">
                <button type="submit" class="btn btn-primary">Submit</button>
            </div>
        </form>

        <table class="table table-condensed">
            <tr>
                <th>Application</th>
                <th>
                    <span class="pull-right">
                        Delete <span class="glyphicon glyphicon-info-sign" aria-hidden="true"
                                     title="Deleting this API key will de-authorize any external applications that use it to connect to the OSF"></span>
                    </span>
                </th>
            </tr>
            %for reg_app in known_apps:
                <tr>
                    <td>
                        <a href="${reg_app.home_url}">${reg_app.name}</a>
                        <p>Key: <span class="text-muted">${reg_app._id} </span></p>
                    </td>
                    <!-- TODO: Add error message for when button deleted -->
                    <td>
                        <button type="button" class="btn btn-danger pull-right">Delete</button>
                    </td>
                </tr>
            %endfor
        </table>
    </div>
</div>

</%def>
