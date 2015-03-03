<!-- Authorization -->
<div>
    <h4 class="addon-title">
        FigShare
        <small class="authorized-by">
            % if authorized:
                    authorized
                <a id="figshareDelKey" class="text-danger pull-right addon-auth">Delete Access Token</a>
            % else:
                <a id="figshareAddKey" class="text-primary pull-right addon-auth">
                    Create Access Token
                </a>
            % endif
        </small>
    </h4>
</div>

<%include file="profile/addon_permissions.mako" />

