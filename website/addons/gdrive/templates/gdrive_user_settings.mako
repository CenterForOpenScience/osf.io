

<div id="driveAddonScope"class="addon-settings scripted">
<h4 class="addon-title">
    Google Drive
    <small>
        <!-- Delete Access Token Button-->
        <span data-bind="if: userHasAuth() && loaded()">
            <a data-bind="click:deleteKey" class="text-danger pull-right addon-auth">
                Delete Access Token
            </a>
        </span>
        <!-- Create Access Token Button -->
        <span data-bind="if: !userHasAuth() && loaded()">
            <a data-bind="click:createAuth" class="text-primary pull-right addon-auth">
                Create Access Token
            </a>
        </span>
    </small>

</h4>


    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>


</div>

##<script>
##    $script(['/static/addons/gdrive/gdriveUserConfig.js'], function() {
##        //Endpoint for Drive user settings
##        var url = '/api/v1/settings/gdrive';
##        // Start up the Drive Config Manager
##        var drive = new GdriveUserConfig('#driveAddonScope', url);
##    });
##
##</script>