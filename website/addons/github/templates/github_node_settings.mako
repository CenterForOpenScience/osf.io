<%inherit file="project/addon/settings.mako" />

<!-- Authorization -->
<div>
    % if authorized_user:
        <a id="githubDelKey" class="btn btn-danger">Delete Access Token</a>
        <span>Authorized by ${authorized_user}</span>
    % else:
        <a id="githubAddKey" class="btn btn-primary">
            % if user_has_authorization:
                Import Token from Profile
            % else:
                Create Access Token
            % endif
        </a>
    % endif
</div>

<br />

<div class="form-group">
    <label for="githubUser">GitHub User</label>
    <input class="form-control" id="githubUser" name="github_user" value="${github_user}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="githubRepo">GitHub Repo</label>
    <input class="form-control" id="githubRepo" name="github_repo" value="${github_repo}" ${'disabled' if disabled else ''} />
</div>

<script type="text/javascript">

    $(document).ready(function() {

        $('#githubAddKey').on('click', function() {
            % if authorized_user:
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'github/user_auth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = nodeApiUrl + 'github/oauth/';
            % endif
        });

        $('#githubDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to delete your GitHub access key?',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: nodeApiUrl + 'github/oauth/delete/',
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
