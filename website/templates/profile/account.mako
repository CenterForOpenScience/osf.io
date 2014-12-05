<%inherit file="base.mako"/>

<%def name="title()">Account Settings</%def>

<%def name="content()">
    <h2 class="page-header">Account Settings</h2>
    <div class="row">
        <div class="col-md-3">
            <div class="panel panel-default">
                <ul class="nav nav-stacked nav-pills">
                    <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                    <li><a href="#">Account Settings</a></li>
                    <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                </ul>
            </div>
        </div>
        <div class="col-md-6">
            <div id="changePassword" class="panel panel-default">
                <div class="panel-heading"><h3 class="panel-title">Change Password</h3></div>
                <div class="panel-body">
                    <form id="changePasswordForm" role="form" action="${ web_url_for('user_account_password') }" method="post">
                        <div class="form-group">
                            <label for="old-password">Old password</label>
                            <input type="password" class="form-control" name="old_password">
                        </div>
                        <div class="form-group">
                            <label for="password">New password</label>
                            <input type="password" class="form-control" name="new_password">
                        </div>
                        <div class="form-group">
                            <label for="password2">Confirm new password</label>
                            <input type="password" class="form-control" name="confirm_password">
                        </div>
                        <button type="submit" class="btn btn-default">Update password</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</%def>
