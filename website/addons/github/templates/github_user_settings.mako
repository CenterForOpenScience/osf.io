
<div id='githubAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
        Github
        <!-- Delete Access Token Button -->
        <small class="authorized-by">
            <span data-bind="if: userHasAuth() && loaded()">
                    authorized
                    <a href="https://github.com/${authorized_github_user}" target="_blank">
                        ${authorized_github_user}
                    </a>
                    <a data-bind="click: deleteKey"
                       class="text-danger pull-right addon-auth">Delete Access Token</a>
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
</div>

<%include file="profile/addon_permissions.mako" />




