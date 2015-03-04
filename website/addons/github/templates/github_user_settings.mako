<!-- Authorization -->
<div>
    <h4 class="addon-title">
        GitHub
        <small class="authorized-by">
            % if authorized:
                    authorized by
                    <a href="https://github.com/${authorized_github_user}" target="_blank">
                        ${authorized_github_user}
                    </a>
                <a id="githubDelKey" class="text-danger pull-right addon-auth">Delete Access Token</a>
            % else:
                <a id="githubAddKey" class="text-primary pull-right addon-auth">
                    Create Access Token
                </a>
            % endif
        </small>
    </h4>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />
