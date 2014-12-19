<%inherit file="base.mako"/>
<%def name="title()">Notifications</%def>
<%def name="content()">
<% import json %>
<% import website%>
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
                            <p class="text-muted" style="padding-left: 15px">Receive general notifications</p>
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
    </div>
</div>

<script type="text/javascript">

    $script(['/static/js/notificationsConfig.js']);
    $script.ready('NotificationsConfig', function() {
        var notifications = new NotificationsConfig('#selectLists', '${website.settings.MAILCHIMP_GENERAL_LIST}');
    });
</script>

</%def>
