## Template for the "Dataverse" section in the "Configure Add-ons" panel

<div id='dataverseAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        Dataverse
        <span data-bind="if: showDeleteAuth">
            <small class="authorized-by">
                authorized by {{ dataverseUsername }}
                    <a data-bind="click: deleteKey" class="text-danger pull-right addon-auth">Disconnect Account</a>

            </small>
        </span>
    </h4>

    <!-- Enter Credentials -->
    <form data-bind="if: showInputCredentials">
        <div class="text-info dataverse-settings" data-bind="if: credentialsChanged">
            Your dataverse credentials may not be valid. Please re-enter your API token.
        </div>
        <div class="form-group">
            <label for="apiToken">
                API Token
                <a href="{{urls().apiToken}}"
                   target="_blank" class="text-muted addon-external-link">
                    (Get from Dataverse <i class="fa fa-external-link-square"></i>)
                </a>
            </label>
            <input class="form-control" name="apiToken" data-bind="value: apiToken"/>
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
