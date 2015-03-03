<%inherit file="base.mako"/>
<%def name="title()">Notifications</%def>
<%def name="content()">
<% import json %>
<% from website import settings%>
<h2 class="page-header">Notifications</h2>

<div class="row">

    <div class="col-md-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                <li><a href="#">Notifications</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-md-6">
        <div class="panel panel-default scripted" id="selectLists">
            <div class="panel-heading"><h3 class="panel-title">Configure Email Preferences</h3></div>
            <div class="panel-body">
                 <h3>Emails</h3>
                    </br>
                    <form>
                        <div class="form-group">

                            <input type="checkbox"
                                   data-bind="checked: subscribed"/>
                            <label data-bind="text: list"></label>
                            <p class="text-muted" style="padding-left: 15px">Receive general notifications about the OSF every 2-3 weeks.</p>
                        </div>
                        <div class="padded">
                        <button
                            type="submit"
                            class="btn btn-success"
                            data-bind="click: submit"
                        >Submit</button>
                        </div>

                    </form>

                    <!-- Flashed Messages -->
                    <div data-bind="html: message, attr: {class: messageClass}"></div>
            </div><!--view model scope ends -->
        </div>
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Configure Notification Preferences</h3></div>
                <form id="selectNotifications" class="osf-treebeard-minimal">
                    <div id="grid">
                            <div class="notifications-loading"> <i class="icon-spinner notifications-spin"></i> <p class="m-t-sm fg-load-message"> Loading notification settings...  </p> </div>
                    </div>
                    <div class="help-block" style="padding-left: 15px">
                            <p id="configureNotificationsMessage"></p>
                    </div>
                </form>
        </div>
    </div>
</div>
</%def>

<%def name="javascript()">
    <% import website %>
    <% import json %>
    ${parent.javascript()}
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'mailingList': '${website.settings.MAILCHIMP_GENERAL_LIST}'});
    </script>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/notifications-config-page.js" | webpack_asset}"></script>
</%def>
