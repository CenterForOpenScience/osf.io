## Template for the "Dataverse" section in the "Configure Add-ons" panel

<div id='dataverseAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
        Dataverse
        <span data-bind="if: showDeleteAuth">
            <small class="authorized-by">
                authorized by {{ dataverseUsername }}
                    <a data-bind="click: deleteKey" class="text-danger pull-right addon-auth">Delete Credentials</a>

            </small>
        </span>
    </h4>

    <!-- Enter Credentials -->
    <form data-bind="if: showInputCredentials">
        <div class="text-info dataverse-settings" data-bind="if: credentialsChanged">
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

<%include file="profile/addon_permissions.mako" />
