<%inherit file="base.mako"/>
<%def name="title()">Application Detail</%def>
<%def name="content()">
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

        <div id="app-detail"> <!-- TODO: Style this to stand apart from page -->

            <div id="app-keys" class=""
                 data-bind="visible: (content().length > 0)">
                <span class="text-muted">Client ID:</span> <span data-bind="text: content().clientId"></span><br>
                <span class="text-muted">Client secret:</span> <span data-bind="text: content().clientSecret"></span>
            </div>
            <div id="app-fields">
                <!-- TODO: Add revoke/ reset buttons -->
                <form role="form">
                    <!-- TODO: Write AJAX or KO endpoint for submission -->
                    <div class="form-group">
                        <label>Application name</label>
                        <input class="form-control" type="text" data-bind="value: content().name">
                    </div>

                    <div class="form-group">
                        <label>Project homepage URL</label>
                        <input class="form-control" type="text" data-bind="value: content().homeUrl">
                    </div>

                    <div class="form-group">
                        <label>Application description</label>
                        <textarea class="form-control" placeholder="Application description is optional" data-bind="value: content().description"></textarea>
                    </div>

                    <div class="form-group">
                        <label>Authorization callback URL</label>
                        <input type="text" class="form-control" data-bind="value: content().callbackUrl">
                    </div>

                    <div class="padded">
                        <button type="submit" class="btn btn-primary"
                                data-bind="visible: !dataUrl, click: $root.createApplication">Create</button>

                        <button type="submit" class="btn btn-primary"
                                data-bind="visible: dataUrl, click: $root.updateApplication">Update</button>
                    </div>
                </form>

                <!-- Flashed Messages -->
                <div class="help-block">
                    <p data-bind="html: message, attr.class: messageClass"></p>
                </div>
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
