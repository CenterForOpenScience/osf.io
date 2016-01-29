
<%inherit file="base.mako"/>

<%def name="title()">Account Settings</%def>

<%def name="stylesheets()">
   ${parent.stylesheets()}
   <link rel="stylesheet" href='/static/css/pages/account-setting-page.css'>
</%def>

<%def name="content()">
    <% from website import settings %>
    <div id="accountSettings">
        <h2 class="page-header">Settings</h2>
        <div class="row">
            <div class="col-md-3 affix-parent">
              <%include file="include/profile/settings_navpanel.mako" args="current_page='account'"/>
            </div>
            <div class="col-md-6">
                <div id="connectedEmails" class="panel panel-default scripted">
                    <div class="panel-heading clearfix"><h3 class="panel-title">Connected Emails</h3></div>
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
                                    <td style="word-break: break-all;">{{ $data.address }}</td>
                                    <td style="width:150px;"><a data-bind="click: $parent.makeEmailPrimary">make&nbsp;primary</a></td>
                                    <td style="width:50px;"><a data-bind="click: $parent.removeEmail"><i class="fa fa-times text-danger"></i></a></td>
                                </tr>
                            </tbody>
                        </table>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th colspan="3">Unconfirmed Emails</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- ko foreach: profile().unconfirmedEmails() -->
                                <tr>
                                    <td style="word-break: break-all;">{{ $data.address }}</td>
                                    <td style="width:150px;"><a data-bind="click: $parent.resendConfirmation">resend&nbsp;confirmation</a></td>
                                    <td style="width:50px;" ><a data-bind="click: $parent.removeEmail"><i class="fa fa-times text-danger"></i></a></td>
                                </tr>
                                <!-- /ko -->
                                <tr>
                                    <td colspan="3">
                                        <form data-bind="submit: addEmail">
                                            <p>
                                            To merge an existing account with this one or to log in with multiple email addresses, add an alternate email address below.
                                            <span class="fa fa-info-circle" data-bind="tooltip: {title: 'Merging accounts will move all projects and components associated with two emails into one account. All projects and components will be displayed under the email address listed as primary.',
                                             placement: 'bottom', container : 'body'}"></span>
                                            </p>
                  
                                            <div class="form-group">
                                                ## email input verification is not supported on safari
                                              <input placeholder="Email address" type="email" data-bind="value: emailInput" class="form-control" required maxlength="254">
                                            </div>
                                            <input type="submit" value="Add Email" class="btn btn-success">
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
                    <div class="panel-heading clearfix"><h3 class="panel-title">Change Password</h3></div>
                    <div class="panel-body">
                        <form id="changePasswordForm" role="form" action="${ web_url_for('user_account_password') }" method="post">
                            <div class="form-group">
                                <label for="old_password">Old password</label>
                                <input type="password" class="form-control" name="old_password" required>
                            </div>
                            <div class="form-group">
                                <label for="new_password">New password</label>
                                <input type="password" class="form-control" name="new_password" required>
                            </div>
                            <div class="form-group">
                                <label for="confirm_password">Confirm new password</label>
                                <input type="password" class="form-control" name="confirm_password" required>
                            </div>
                            <button type="submit" class="btn btn-primary">Update password</button>
                        </form>
                    </div>
                </div>
                <div class="panel panel-default">
                  <div class="panel-heading clearfix"><h3 class="panel-title">Security Settings</h3></div>
                  <div class="panel-body">
                    % for addon in addons:
                    ${render_user_settings(addon) }
                    % if not loop.last:
                    <hr />
                    % endif
                    % endfor
                  </div>
                </div>
                <div id="exportAccount" class="panel panel-default">
                    <div class="panel-heading clearfix"><h3 class="panel-title">Export Account Data</h3></div>
                    <div class="panel-body">
                        <p>Exporting your account data allows you to keep a permanent copy of the current state of your account. Keeping a copy of your account data can provide peace of mind or assist in transferring your information to another provider.</p>
                        <a class="btn btn-primary" data-bind="click: submit, css: success() === true ? 'disabled' : ''">Request Export</a>
                    </div>
                </div>
                <div id="deactivateAccount" class="panel panel-default">
                    <div class="panel-heading clearfix"><h3 class="panel-title">Deactivate Account</h3></div>
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

<%def name="stylesheets()">
  ${parent.stylesheets()}
  % for stylesheet in addons_css:
      <link rel="stylesheet" type="text/css" href="${stylesheet}">
  % endfor
</%def>

<%def name="render_user_settings(config)">
    <%
       template = config['user_settings_template']
       tpl = template.render(**config)
    %>
    ${ tpl | n }
</%def>

<%def name="javascript_bottom()">
    ## Webpack bundles
    % for js_asset in addons_js:
      <script src="${js_asset | webpack_asset}"></script>
    % endfor
</%def>
