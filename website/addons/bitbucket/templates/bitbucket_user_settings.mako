<%inherit file="project/addon/settings.mako" />

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
            bootbox.confirm(
                'Are you sure you want to delete your Bitbucket access key?',
                function(result) {
                    if (result) {
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
            )
        });
    });

</script>
