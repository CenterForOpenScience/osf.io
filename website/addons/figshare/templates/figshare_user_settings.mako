<%inherit file="project/addon/settings.mako" />

<!-- Authorization -->
<div>
    % if authorized:
        <a id="figshareDelKey" class="btn btn-danger">Delete Access Token</a>
    % else:
        <a id="figshareAddKey" class="btn btn-primary">
            Create Access Token
        </a>
    % endif
</div>

<script type="text/javascript">

    $(document).ready(function() {

        $('#figshareAddKey').on('click', function() {
            % if authorized_user:
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
                window.location.href = '/api/v1/settings/figshare/oauth/';
            % endif
        });

        $('#figshareDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to delete your Figshare access key? This will ' +
                    'revoke access to Figshare for all projects you have authorized.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: '/api/v1/settings/figshare/oauth/delete/',
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