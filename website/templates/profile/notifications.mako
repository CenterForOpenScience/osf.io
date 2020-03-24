<%inherit file="base.mako"/>
<%def name="title()">${_("Notifications")}</%def>

<%def name="content()">
<% from website import settings%>
<h2 class="page-header">${_("Settings")}</h2>

<div id="notificationSettings" class="row">
    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako" args="current_page='notifications'"/>
    </div>

    <div class="col-sm-9 col-md-7">
        <div style="display: none;">
        <div class="panel panel-default scripted" id="selectLists">
            <div class="panel-heading clearfix"><h3 class="panel-title">${_("Configure Email Preferences")}</h3></div>
            <div class="panel-body">
                 <h3>Emails</h3>
                    </br>
                    <form>
                        <div class="form-group">
                            <input type="checkbox"
                                data-bind="checked: subscribed"
                                value="${settings.MAILCHIMP_GENERAL_LIST}"/>
                              <label>${settings.MAILCHIMP_GENERAL_LIST}</label>
                            <p class="text-muted" style="padding-left: 15px">${_("Receive general notifications about the GakuNin RDM every 2-3 weeks.")}</p>
                        </div>
                    </form>
                    <form>
                        <div class="form-group">
                            <input type="checkbox"
                                data-bind="checked: subscribed"
                                value="${settings.OSF_HELP_LIST}"/>
                              <label>${settings.OSF_HELP_LIST}</label>
                            <p class="text-muted" style="padding-left: 15px">${_("Receive helpful tips on how to make the most of the GakuNin RDM, up to once per week.")}</p>
                        </div>
                        <div class="p-t-md p-b-md">
                        <button
                            type="submit"
                            class="btn btn-success"
                            data-bind="click: submit"
                        >Save</button>
                        </div>

                    </form>

                    <!-- Flashed Messages -->
                    <div data-bind="html: message, attr: {class: messageClass}"></div>
            </div><!--view model scope ends -->
        </div>
        </div>
        <div class="panel panel-default">
            <div class="panel-heading clearfix"><h3 class="panel-title">${_("Configure Notification Preferences")}</h3></div>
            <div class="panel-body">
                <div class="help-block">
                     <p class="text-muted"> ${_("NOTE: Regardless of your selected preferences, GakuNin RDM will continue to provide transactional and administrative service emails.")}</p>
                </div>
                <form id="selectNotifications" class="osf-treebeard-minimal">
                    <div id="grid">
                        <div class="spinner-loading-wrapper">
                            <div class="ball-scale ball-scale-blue">
                                <div></div>
                            </div>
                            <p class="m-t-sm fg-load-message"> ${_("Loading notification settings...")} </p>
                        </div>
                    </div>
                    <div class="help-block" style="padding-left: 15px">
                            <p id="configureNotificationsMessage"></p>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
</%def>

<%def name="javascript()">
    <% import website %>
    ${parent.javascript()}
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {
            'mailingLists': ${ [website.settings.MAILCHIMP_GENERAL_LIST, website.settings.OSF_HELP_LIST] | sjson, n }
        });
    </script>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/notifications-config-page.js" | webpack_asset}"></script>
</%def>
