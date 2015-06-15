<%inherit file="base.mako"/>
<%def name="title()">Application Detail</%def>
<%def name="content()">
<style type="text/css">
    .border-box {
        padding: 15px 10px;
        border-radius: 4px;
        border: solid #DDD;
        border-width: 1px 0;
        line-height: 1.1;
        display: block;
        margin-bottom: 1em;
    }
</style>

<h2 class="page-header">OAuth Application Settings</h2>

<div class="row">

    <div class="col-sm-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
                <li><a href="${ web_url_for('oauth_application_config') }">Developer apps</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-sm-9 col-md-7">

        <div id="app-detail" data-bind="with: content()">
            <div id="app-keys" class="border-box text-right text-muted"
                 data-bind="visible: $root.dataUrl">
                <p><span><strong>Client ID</strong>:</span> <br><span data-bind="text: clientId"></span></p>
                <p><span><strong>Client secret</strong>:</span> <br><span data-bind="text: clientSecret"></span></p>
            </div>
            <div id="app-fields">
                <!-- TODO: Add revoke/ reset buttons -->
                <form role="form" data-bind="validationOptions: {insertMessages: false, messagesOnModified: false}">
                    <div class="form-group">
                        <label>Application name</label>
                        <input class="form-control" type="text" data-bind="value: name" placeholder="Required">
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: name"></p>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Project homepage URL</label>
                        <input class="form-control" type="text" data-bind="value: homeUrl" placeholder="Required">
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: homeUrl"></p>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Application description</label>
                        <textarea class="form-control" placeholder="Application description is optional" data-bind="value: description"></textarea>
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: description"></p>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Authorization callback URL</label>
                        <input type="text" class="form-control" data-bind="value: callbackUrl" placeholder="Required">
                        <div data-bind="visible: $root.showMessages, css:'text-danger'">
                            <p data-bind="validationMessage: callbackUrl"></p>
                        </div>
                    </div>

                    <!-- Flashed Messages -->
                    <div class="help-block">
                        <p data-bind="html: $root.message, attr.class: $root.messageClass"></p>
                    </div>

                    <div class="padded">
                        <button type="submit" class="btn btn-primary"
                                data-bind="visible: !$root.dataUrl, click: $root.createApplication">Create</button>

                        <button type="submit" class="btn btn-primary"
                                data-bind="visible: $root.dataUrl, click: $root.updateApplication">Update</button>
                    </div>
                </form>
            </div>
        </div> <!-- End app-detail section -->
    </div>
</div>
</%def>

<%def name="javascript_bottom()">
<script type="text/javascript">
   ## Store mako variables on window so they are accessible from JS
   ## modules. Not sure if this is a good idea.
   window.contextVars = window.contextVars || {};
   window.contextVars.urls = {
       dataUrl: ${detail_url},
       submitUrl: ${submit_url}
   };
</script>
<script src=${"/static/public/js/profile-settings-applications-detail-page.js" | webpack_asset}></script>
</%def>
