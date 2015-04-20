

<div id="googleDriveAddonScope" class="addon-settings scripted">
<h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
    Google Drive
    <small>
        <!-- Delete Access Token Button-->
        <span data-bind="if: userHasAuth() && loaded()">
            authorized
            <span data-bind="if: username()">by {{ username }}</span>
            <a data-bind="click:deleteKey" class="text-danger pull-right addon-auth">
               Disconnect Acount
            </a>
        </span>
        <!-- Create Access Token Button -->
        <span data-bind="if: !userHasAuth() && loaded()">
            <a data-bind="attr.href: urls().create" class="text-primary pull-right addon-auth">
            Connect Account
            </a>
        </span>
    </small>

</h4>
    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>
</div>

<%include file="profile/addon_permissions.mako" />
