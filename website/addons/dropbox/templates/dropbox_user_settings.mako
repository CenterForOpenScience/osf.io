## Template for the "Dropbox" section in the "Configure Add-ons" panel
<%inherit file="project/addon/user_settings.mako"/>

<div class='addon-settings'>
    % if has_auth:
        <a href="${api_url_for('dropbox_oauth_delete_user')}" class="btn btn-danger">
            Delete Access Token
        </a>
        <div class="help-block">
            Authorized by Dropbox user
        </div>
    %else:
        <a href="${api_url_for('dropbox_oauth_start__user')}" class="btn btn-primary">Create Access Token</a>
    % endif

</div>

## TODO(sloria): remove these from parent template?
<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>
