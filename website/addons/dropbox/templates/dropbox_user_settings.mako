## Template for the "Dropbox" section in the "Configure Add-ons" panel
<%inherit file="project/addon/user_settings.mako"/>

<div id='dropboxAddonScope' class='addon-settings'>
    % if has_auth:
        <button data-bind='click: deleteKey' class="btn btn-danger">
            Delete Access Token
        </button>
        <div class="help-block">
            Authorized by Dropbox user
        </div>
    %else:
        <a href="${api_url_for('dropbox_oauth_start__user')}" class="btn btn-primary">Create Access Token</a>
    % endif
</div>

<script>
    $(function() {
        var language = $.osf.Language.Addons.dropbox;
        var deleteAuthURL = '${api_url_for("dropbox_oauth_delete_user")}';
        var DropboxViewModel = {
            'deleteKey': function() {
                bootbox.confirm({
                    title: 'Delete Dropbox Token?',
                    message: language.confirmDeauth,
                    callback: function(confirmed) {
                        return $.ajax({
                            url: deleteAuthURL,
                            type: 'DELETE'
                        })
                        .done(function() {
                            // TODO(sloria): Just reloading the page here to
                            // be consistent with the other addons, but it
                            // isn't necessary. Pending discussion about
                            // settings page interface.
                            window.location.reload();
                        });
                    }
                });
            }
        }
        ko.applyBindings(DropboxViewModel, $('#dropboxAddonScope')[0]);
    })
</script>

## TODO(sloria): remove these from parent template?
<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>
