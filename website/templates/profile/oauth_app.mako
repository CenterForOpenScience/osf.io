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

        <!-- TODO: Add list of known registered apps below -->
        <div id="placeholder">Empty placeholder for registered apps</div>
        <table>
            <tr>
                <th>App name</th>
                <th>Reg date</th>
                <th><!-- Show key --></th>
                <th><!-- Delete button --></th>
            </tr>
            %for a in known_apps:
                <tr>
                    <td>${a.name}</td>
                    <td>${a.reg_date}</td>
                    <td>Show</td>
                    <td>x</td>
                </tr>
            %endfor
        </table>

        Known apps: ${known_apps} .
    </div>
</div>

</%def>
