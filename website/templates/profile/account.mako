
<%inherit file="base.mako"/>

<%def name="title()">Account Settings</%def>

<%def name="content()">
    <% from website import settings %>
    <div id="accountSettings">
        <h2 class="page-header">Account Settings</h2>
        <div class="row">
            <div class="col-sm-3 affix-parent">
                    <div class="osf-affix profile-affix" data-spy="affix" data-offset-top="70" data-offset-bottom="268">
                        <ul class="nav nav-stacked nav-pills">
                            <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                            <li class="active"><a href="#">Account Settings</a></li>
                            <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                            <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
                        </ul>
                </div>
            </div>
            <div class="col-md-6">
                <div id="connectedEmails" class="panel panel-default scripted">
                    <div class="panel-heading"><h3 class="panel-title">Connected Emails</h3></div>
                    <div class="panel-body">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th colspan="2">Primary Email</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{{ profile().primaryEmail().address }}</td>
                                    <td></td>
                                </tr>
                            </tbody>
                        </table>

                        <table class="table">
                            <thead>
                                <tr>
                                    <th colspan="3">Alternate Emails</th>
                                </tr>
                            </thead>
                            <tbody data-bind="foreach: profile().alternateEmails()">
                                <tr>
                                    <td style="width:100%">{{ $data.address }}</td>
                                    <td><a data-bind="click: $parent.makeEmailPrimary">make&nbsp;primary</a></td>
                                    <td><a data-bind="click: $parent.removeEmail"><i class="fa fa-times text-danger"></i></a></td>
                                </tr>
                            </tbody>
                        </table>

                        <table class="table">
                            <thead>
                                <tr>
                                    <th colspan="2">Unconfirmed Emails</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- ko foreach: profile().unconfirmedEmails() -->
                                <tr>
                                    <td style="width:100%">{{ $data.address }}</td>
                                    <td><a data-bind="click: $parent.removeEmail"><i class="fa fa-times text-danger"></i></a></td>
                                </tr>
                                <!-- /ko -->
                                <tr>
                                    <td colspan="2">
                                        <form data-bind="submit: addEmail">
                                            <div class="form-group">
                                              <input placeholder="Email address" data-bind="value: emailInput" class="form-control">
                                            </div>
                                            <input type="submit" value="Add Email" class="btn btn-default">
                                        </form>
                                        <div class="help-block">
                                            <p data-bind="html: message, attr: {class: messageClass}"></p>
                                        </div>
                                    </td>

                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="changePassword" class="panel panel-default">
                    <div class="panel-heading"><h3 class="panel-title">Change Password</h3></div>
                    <div class="panel-body">
                        <form id="changePasswordForm" role="form" action="${ web_url_for('user_account_password') }" method="post">
                            <div class="form-group">
                                <label for="old_password">Old password</label>
                                <input type="password" class="form-control" name="old_password">
                            </div>
                            <div class="form-group">
                                <label for="new_password">New password</label>
                                <input type="password" class="form-control" name="new_password">
                            </div>
                            <div class="form-group">
                                <label for="confirm_password">Confirm new password</label>
                                <input type="password" class="form-control" name="confirm_password">
                            </div>
                            <button type="submit" class="btn btn-default">Update password</button>
                        </form>
                    </div>
                </div>
                <div id="exportAccount" class="panel panel-default">
                    <div class="panel-heading"><h3 class="panel-title">Export Account Data</h3></div>
                    <div class="panel-body">
                        <p>Exporting your account data allows you to keep a permanent copy of the current state of your account. Keeping a copy of your account data can provide peace of mind or assist in transferring your information to another provider.</p>
                        <a class="btn btn-default" data-bind="click: submit, css: success() === true ? 'disabled' : ''">Request Export</a>
                    </div>
                </div>
                <div id="deactivateAccount" class="panel panel-default">
                    <div class="panel-heading"><h3 class="panel-title">Deactivate Account</h3></div>
                    <div class="panel-body">
                        <p class="alert alert-warning"><strong>Warning:</strong> This action is irreversible.</p>
                        <p>Deactivating your account will remove you from all public projects to which you are a contributor. Your account will no longer be associated with OSF projects, and your work on the OSF will be inaccessible.</p>
                        <a class="btn btn-danger" data-bind="click: submit, css: success() === true ? 'disabled' : ''">Request Deactivation</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src=${"/static/public/js/profile-account-settings-page.js" | webpack_asset}></script>
</%def>
