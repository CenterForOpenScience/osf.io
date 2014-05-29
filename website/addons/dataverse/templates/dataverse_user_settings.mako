## Template for the "Dataverse" section in the "Configure Add-ons" panel

<h4 class="addon-title">Dataverse</h4>


<div id='dataverseAddonScope' class='addon-settings scripted'>

    <!-- Delete Access Token Button -->
     <div data-bind="if: userHasAuth() && loaded() && connected()">
        <div class="well well-sm">
            Authorized by Dataverse user {{ dataverseUsername }}
            <a data-bind="click: deleteKey" class="text-danger pull-right" style="cursor: pointer">Delete Credentials</a>
        </div>
    </div>

    <!-- Create Access Token Button -->
    <form data-bind="if: !userHasAuth() && loaded() || !connected()">
        <div class="text-danger" data-bind="if: userHasAuth() && !connected()">
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