<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}">
        figshare
        <small class="authorized-by">
            % if authorized:
                    authorized by <em> ${name} </em>
                <a id="figshareDelKey" class="text-danger pull-right addon-auth">Disconnect Account</a>
            % else:
                <a id="figshareAddKey" class="text-primary pull-right addon-auth">
                Connect Account
                </a>
            % endif
        </small>
    </h4>
</div>

<%include file="profile/addon_permissions.mako" />

