<%inherit file="base.mako"/>

<%def name="title()">Account Settings</%def>

<%def name="content()">
    <% from website import settings %>
    <h2 class="page-header">Account Settings</h2>
    <div class="row">
        <div class="col-md-3">
            <div class="panel panel-default">
                <ul class="nav nav-stacked nav-pills">
                    <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                    <li><a href="#">Account Settings</a></li>
                    <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                    <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
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
            <div id="deactivateAccount" class="panel panel-default">
                <div class="panel-heading"><h3 class="panel-title">Deactivate Account</h3></div>
                <div class="panel-body">
                    <p>If you choose to deactivate your OSF account: </p>
                        <ul>
                            <li>You will not be visible in search.</li>
                            <li>Your profile page will be deleted.</li>
                            <li>You will not be able to access private resources available to your account.</li>
                            <li>New accounts may not be registered for any email associated with your account.</li>
                        </ul>
                    <p></p>
                    <p class="alert alert-danger"><strong>Warning:</strong> Deactivating your OSF account should be considered a permanent action.</p>
                    <div class="form-group">
                        <label for="verifyAccountId">Please verify your account ID (<code>{{ accountId }}</code>):</label>
                        <input data-bind="value: verifyId" name="verifyAccountId" class="form-control">
                    </div>
                    <a data-bind="click: submit" class="btn btn-danger">Deactivate Account</a>
                </div>
            </div>
        </div>
    </div>
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script src="${"profile-settings-account-page" | webpack_asset}"></script>
</%def>
