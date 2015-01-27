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
            <div class="panel-body">
                <form id="selectNotifications">
                    <h4>User Notifications</h4>
                    <div class="row" style="font-weight: bold">
                        <div class="col-md-6">Notifications</div>
                        <div class="col-md-6">Notification Type</div>
                    </div>
                    % for subscription in user_subscriptions_available:
                    <div class="form-group" id="${user_subscriptions['id']}">
                    <div class="row">
                        <div class="col-md-6">
                            <label style="font-weight:normal; padding-right: 50px">
                                ${user_subscriptions_available[subscription]}
                            </label>
                         </div>

                        <div class="col-md-6">
                            <select class="form-control" name="${subscription}">
                                <option value="none" ${'selected' if user_subscriptions['subscriptions'] == [] else ''}>
                                    None
                                </option>
                                <option value="email_transactional" ${'selected' if 'email_transactional' in user_subscriptions['subscriptions'][subscription] else ''}>
                                    Receive emails immediately
                                </option>
                                <option value="email_digest" ${'selected' if 'email_digest' in user_subscriptions['subscriptions'][subscription] else ''}>
                                    Receive in a daily email digest
                                </option>
                            </select>
                        </div>
                    </div>
                    </div>
                    % endfor
                    <br/>
                    <h4>Project Notifications</h4>
                    % if node_subscriptions['node_subscriptions']['children']:
                        <div class="row" style="font-weight: bold">
                            <div class="col-md-6">Notifications</div>
                            <div class="col-md-6">Notification Type</div>
                        </div>
                        ${format_subscriptions(node_subscriptions['node_subscriptions']['children'], indent=0)}
                     %else:
                        You are not receiving any notifications from your OSF projects.
                     % endif

                <div class="padded">
                    <button class="btn btn-success">Submit</button>
                </div>
                <div class="help-block">
                        <p id="configureNotificationsMessage"></p>
                </div>
                </form>
            </div>
        </div>
    </div>
</div>
</%def>

<%def name="format_subscriptions(d_to_use, indent=0)">
    <% from website.models import Node %>
    %for node_id in d_to_use.keys():
        <div class="form-group" id="${node_id}">
            %for i in range(indent):
                &emsp;
            %endfor
            <a href="${Node.load(node_id).url}">${Node.load(node_id).title}</a>
            <br/>

            % for subscription in node_subscriptions_available:
                <div class="col-md-6">
                %for i in range(indent):
                    &emsp;
                %endfor
                <label style="font-weight:normal; padding-right: 50px">
                                ${node_subscriptions_available[subscription]}
                </label>
                </div>

                <div class="col-md-6">

                    <select class="form-control" name="${subscription}">
                        <option value="none" ${'selected' if 'email_transactional' not in d_to_use[node_id]['subscriptions'][subscription] and 'email_digest' not in d_to_use[node_id]['subscriptions'][subscription] else ''}>None</option>
                        <option value="email_transactional" ${'selected' if 'email_transactional' in d_to_use[node_id]['subscriptions'][subscription] else ''}>
                            Receive emails immediately
                        </option>
                        <option value="email_digest" ${'selected' if 'email_digest' in d_to_use[node_id]['subscriptions'][subscription] else ''}>
                            Receive in a daily email digest
                        </option>
                    </select>

                </div>
            % endfor
                <hr>
            %if d_to_use[node_id]['children'] != {}:
                ${format_subscriptions(d_to_use[node_id]['children'], indent=indent+1)}
            %endif
    </div>
    %endfor
</%def>

<%def name="javascript()">
    <% import website %>
    ${parent.javascript()}
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'mailingList': '${website.settings.MAILCHIMP_GENERAL_LIST}'});
    </script>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/notifications-config-page.js" | webpack_asset}"></script>
    <script src="${"/static/public/js/osf-notifications-config-page.js" | webpack_asset}"></script>
</%def>
