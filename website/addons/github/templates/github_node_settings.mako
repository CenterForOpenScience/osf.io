<%inherit file="project/addon/settings.mako" />

<!-- Authorization -->
<div>
    <div class="alert alert-danger alert-dismissable">
    <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        Authorizing this GitHub add-on will grant all contributors on this ${node['category']}
        permission to upload, modify, and delete files on the associated GitHub repo.
    </div>
    <div class="alert alert-danger alert-dismissable">
        <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
        If one of your collaborators removes you from this ${node['category']},
        your authorization for GitHub will automatically be revoked.
    </div>
    % if authorized_user:
        <a id="githubDelKey" class="btn btn-danger">Unauthorize: Delete Access Token</a>
        <span>Authorized by ${authorized_user}</span>
    % else:
        <a id="githubAddKey" class="btn btn-primary">
            % if user_has_authorization:
                Authorize: Import Token from Profile
            % else:
                Authorize: Create Access Token
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
                'Are you sure you want to delete your GitHub access key? This will ' +
                    'revoke the ability to modify and upload files to GitHub. If ' +
                    'the associated repo is private, this will also disable viewing ' +
                    'and downloading files from GitHub.',
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
