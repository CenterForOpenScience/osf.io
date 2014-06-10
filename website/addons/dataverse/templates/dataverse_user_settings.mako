## Template for the "Dataverse" section in the "Configure Add-ons" panel

<div id='dataverseAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
        Dataverse
        <span data-bind="if: showDeleteAuth">
            <small class="authorized-by">
                authorized by {{ dataverseUsername }}
                <span data-bind="ifnot: showInputCredentials">
                    <a data-bind="click: deleteKey"
                        class="text-danger pull-right"
                            style="margin-top: 4.8px">Delete Credentials</a>
                </span>
            </small>
        </span>
    </h4>

    <!-- Create Access Token Button -->
    <form data-bind="if: showInputCredentials">
        <div class="text-danger" style="padding-bottom: 10px" data-bind="if: credentialsChanged">
            Your dataverse credentials may not be valid. Please re-enter your password.
        </div>

        <div class="form-group">
            <label for="dataverseUsername">Dataverse Username</label>
            <input class="form-control" name="dataverseUsername" data-bind="value: dataverseUsername"/>
        </div>
        <div class="form-group">
            <label for="dataversePassword">Dataverse Password</label>
            <input class="form-control" type="password" name="dataversePassword" data-bind="value: dataversePassword" />
        </div>
        <button data-bind="click: sendAuth" class="btn btn-success">
            Submit
        </button>
        <span data-bind="if: showDeleteAuth">
            <a data-bind="click: deleteKey"
                class="btn btn-danger pull-right">Delete Credentials</a>
        </span>
    </form>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>


<script>
    $script(['/static/addons/dataverse/dataverseUserConfig.js'], function() {
        // Endpoint for Dataverse user settings
        var url = '/api/v1/settings/dataverse/';
        // Start up the DataverseConfig manager
        var dataverse = new DataverseUserConfig('#dataverseAddonScope', url);
    });
</script>