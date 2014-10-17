<%inherit file="project/addon/node_settings.mako" />

<!-- Authorization -->
<div>
    % if authorized_user:
        <a id="bitbucketDelKey" class="btn btn-danger">Delete Access Token</a>
        <span>Authorized by ${authorized_user}</span>
    % else:
        <a id="bitbucketAddKey" class="btn btn-primary">
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
    <label for="bitbucketUser">Bitbucket User</label>
    <input class="form-control" id="bitbucketUser" name="bitbucket_user" value="${bitbucket_user}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="bitbucketRepo">Bitbucket Repo</label>
    <input class="form-control" id="bitbucketRepo" name="bitbucket_repo" value="${bitbucket_repo}" ${'disabled' if disabled else ''} />
</div>

<script type="text/javascript">

    $(document).ready(function() {

        $('#bitbucketAddKey').on('click', function() {
            % if authorized_user:
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 'bitbucket/user_auth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = nodeApiUrl + 'bitbucket/oauth/';
            % endif
        });

        $('#bitbucketDelKey').on('click', function() {
            bootbox.confirm({
                title: 'Remove access key?',
                message: 'Are you sure you want to remove your Bitbucket access key?',
                callback: function(result) {
                    if(result) {
                        $.ajax({
                            url: nodeApiUrl + 'bitbucket/oauth/delete/',
                            type: 'POST',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            });
        });
    });

</script>
