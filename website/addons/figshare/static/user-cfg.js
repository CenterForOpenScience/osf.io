$(document).ready(function() {

        $('#figshareAddKey').on('click', function() {
            if (window.contextVars.node.authorized_user) {
                $.ajax({
                    type: 'POST',
                    url: '/api/v1/profile/settings/oauth/',
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function (response) {
                        window.location.reload();
                    }
                });
            } else {
                window.location.href = '/api/v1/settings/figshare/oauth/';
            }
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