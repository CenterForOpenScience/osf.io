<!-- Authorization -->
<div>
    <h4 class="addon-title">
        FigShare
        <small class="authorized-by">
            % if authorized:
                    authorized
                <a id="figshareDelKey" class="text-danger pull-right addon-auth">Delete Access Token</a>
            % else:
                <a id="figshareAddKey" class="text-primary pull-right addon-auth">
                    Create Access Token
                </a>
            % endif
        </small>
    </h4>
    <!-- Flashed Messages -->
    <div class="help-block figshare-message"></div>
</div>

<%include file="profile/addon_permissions.mako" />

<script type="text/javascript">

    $.ajax({
            type: 'GET',
            url: '/api/v1/settings/figshare/oauth/check',
            contentType: 'application/json',
            dataType: 'json',
            success: function(response) {
                if (!response) {
                    $("div.figshare-message").html("<p class='text-warning'>Could not retrieve Figshare settings at" +
                            " this time. The Figshare addon credentials may no longer be valid." +
                            " Try deauthorizing and reauthorizing Figshare. </p>");
                } else if ("${has_auth}" === 'True' && "${nodes}" == '[]') {
                    $("div.figshare-message").html("<p class='text-success addon-message'>" +
                    "Add-on successfully authorized. To link this add-on to an OSF project, go to the" +
                    " settings page of the project, enable Figshare, and choose content to connect.</p>")
                }
        }});

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
            bootbox.confirm({
                title: 'Remove access key?',
                message: 'Are you sure you want to remove your Figshare access key? This will ' +
                        'revoke access to Figshare for all projects you have authorized.',
                callback: function(result) {
                    if(result) {
                        $.ajax({
                            url: '/api/v1/settings/figshare/oauth/',
                            type: 'DELETE',
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
