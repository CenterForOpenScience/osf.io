## Template for the "Box" section in the "Configure Add-ons" panel
<div id='boxAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
        Box
        <!-- Delete Access Token Button -->
        <small class="authorized-by">
            <span data-bind="if: userHasAuth() && loaded()">
                    authorized
                    <span data-bind="if: boxName()">by {{ boxName }}</span>
                    <a data-bind="click: deleteKey" class="text-danger pull-right addon-auth">Delete Access Token</a>
            </span>

            <!-- Create Access Token Button -->
            <span data-bind="if: !userHasAuth() && loaded()">
                <a data-bind="attr: {href: urls().create}"
                   class="text-primary pull-right addon-auth">Create Access Token</a>
            </span>
        </small>
    </h4>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>

<%include file="profile/addon_permissions.mako" />
