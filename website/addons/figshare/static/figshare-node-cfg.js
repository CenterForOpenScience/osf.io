var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('osfHelpers');

    $(document).ready(function() {

        $('#figshareAddKey').on('click', function() {
            if ($(this)[0].outerText == 'Authorize: Create Access Token')
                window.location.href = nodeApiUrl + 'figshare/oauth/';
            $.ajax({
                type: 'POST',
                url: nodeApiUrl + 'figshare/user_auth/',
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    window.location.reload();
                }
            });

        });

        $('#figshareDelKey').on('click', function() {
            bootbox.confirm({
                title: 'Remove access key?',
                message: 'Are you sure you want to remove your figshare access key? This will ' +
                'revoke the ability to modify and upload files to figshare. If ' +
                'the associated repo is private, this will also disable viewing ' +
                'and downloading files from figshare.',
                callback: function(result) {
                    if(result) {
                        $.ajax({
                            url: nodeApiUrl + 'figshare/oauth/',
                            type: 'DELETE',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                },
                buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
                }
            });
        });

        $('#figshareSelectProject').on('change', function() {
            var value = $(this).val();
            if (value) {
                $('#figshareId').val(value)
                $('#figshareTitle').val($('#figshareSelectProject option:selected').text())
            }
        });

        $('#addonSettingsFigshare .addon-settings-submit').on('click', function() {
            if ($('#figshareId').val() == '-----') {
                return false;
            }
        });

    });
