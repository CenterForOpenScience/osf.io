<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        figshare
        <small class="authorized-by">
            % if authorized:
                    authorized by <a href=${profile_url}><em> ${name} </em></a>
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

