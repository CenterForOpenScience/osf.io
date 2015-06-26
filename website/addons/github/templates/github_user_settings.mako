<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        GitHub
        <small class="authorized-by">
            % if authorized:
                    authorized by
                    <a href="https://github.com/${authorized_github_user}" target="_blank">
                        ${authorized_github_user}
                    </a>
                <a id="githubDelKey" class="text-danger pull-right addon-auth">Disconnect Account</a>
            % else:
                <a id="githubAddKey" class="text-primary pull-right addon-auth">
                    Connect Account
                </a>
            % endif
        </small>
    </h4>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />
