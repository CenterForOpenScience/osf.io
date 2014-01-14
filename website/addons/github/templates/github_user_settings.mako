<%inherit file="project/addon/settings.mako" />

<!-- Authorization -->
<div>
    % if authorized:
        <a id="githubDelKey" class="btn btn-danger">Delete Access Token</a>
        <div style="padding-top: 10px;">
            Authorized by GitHub user
            <a href="https://github.com/${github_user}" target="_blank">
                ${github_user}
            </a>
        </div>
    % else:
        <a id="githubAddKey" class="btn btn-primary">
            Create Access Token
        </a>
    % endif
</div>

<script type="text/javascript">

    $(document).ready(function() {

        $('#githubAddKey').on('click', function() {
            % if authorized_user_id:
                $.ajax({
                    type: 'POST',
                    url: '/api/v1/profile/settings/oauth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = '/api/v1/settings/github/oauth/';
            % endif
        });

        $('#githubDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to delete your GitHub access key? This will ' +
                    'revoke access to GitHub for all projects you have authorized ' +
                    'and delete your access token from GitHub.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: '/api/v1/settings/github/oauth/delete/',
                            type: 'POST',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            )
        });
    });

</script>
