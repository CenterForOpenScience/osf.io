<%inherit file="project/addon/user_settings.mako" />

<!-- Authorization -->
<div>
    % if authorized:
        <a id="bitbucketDelKey" class="btn btn-danger">Delete Access Token</a>
    % else:
        <a id="bitbucketAddKey" class="btn btn-primary">
            Create Access Token
        </a>
    % endif
</div>

<script type="text/javascript">

    $(document).ready(function() {

        $('#bitbucketAddKey').on('click', function() {
            % if authorized_user:
                $.ajax({
                    type: 'POST',
                    url: '/api/v1/settings/bitbucket/oauth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        window.location.reload();
                    }
                });
            % else:
                window.location.href = '/api/v1/settings/bitbucket/oauth/';
            % endif
        });

        $('#bitbucketDelKey').on('click', function() {
            bootbox.confirm({
                title: 'Remove access key?',
                message: 'Are you sure you want to remove your Bitbucket access key?',
                callback: function(result) {
                    if(result) {
                        $.ajax({
                            url: '/api/v1/settings/bitbucket/oauth/delete/',
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
