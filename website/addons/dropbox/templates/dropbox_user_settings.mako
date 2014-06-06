## Template for the "Dropbox" section in the "Configure Add-ons" panel



<div id='dropboxAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
        Dropbox
        <!-- Delete Access Token Button -->
        <span data-bind="if: userHasAuth() && loaded()">
            <small class="authorized-by">
                authorized
                <span data-bind="if: dropboxName()">by {{ dropboxName }}</span>
                <button data-bind="click: deleteKey"
                   class="btn btn-danger pull-right">Delete Access Token</button>
            </small>
        </span>

        <!-- Create Access Token Button -->
        <span data-bind="if: !userHasAuth() && loaded()">
            <small class="authorized-by">
                <a data-bind="attr: {href: urls().create}"
                   class="btn btn-primary pull-right">Create Access Token</a>
            </small>
        </span>
    </h4>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>


<script>
    $script(['/static/addons/dropbox/dropboxUserConfig.js'], function() {
        // Endpoint for dropbox user settings
        var url = '/api/v1/settings/dropbox/';
        // Start up the Dropbox Config manager
        var dropbox = new DropboxUserConfig('#dropboxAddonScope', url);
    });
</script>

